import bisect

import numpy as np
from loguru import logger
from mass_spec_utils.data_import.mzml import MZMLFile
from sklearn import linear_model
from sklearn.preprocessing import PolynomialFeatures

from vimms.Controller.topN import TopNController
from vimms.PeakDetector import calculate_window_change
from vimms.Roi import match, Roi, SmartRoi
from copy import deepcopy


class RoiController(TopNController):
    """
    An ROI based controller with multiple options
    """

    def __init__(self, ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                 min_roi_length, N, rt_tol=10, min_roi_length_for_fragmentation=1, length_units="scans", ms1_shift=0,
                 params=None):
        super().__init__(ionisation_mode, N, isolation_width, mz_tol, rt_tol, min_ms1_intensity, ms1_shift=ms1_shift,
                         params=params)

        # ROI stuff
        self.min_roi_intensity = min_roi_intensity
        self.mz_units = 'ppm'
        self.min_roi_length = min_roi_length
        self.min_roi_length_for_fragmentation = min_roi_length_for_fragmentation
        self.length_units = length_units

        # Create ROI
        self.live_roi = []
        self.dead_roi = []
        self.junk_roi = []
        self.live_roi_fragmented = []
        self.live_roi_last_rt = []  # last fragmentation time of ROI

        # fragmentation to Roi dictionaries
        self.frag_roi_dicts = []  # scan_id, roi_id, precursor_intensity
        self.roi_id_counter = 0

    def get_rois(self):
        return self.live_roi + self.dead_roi

    def _process_scan(self, scan):
        # if there's a previous ms1 scan to process
        new_tasks = []
        ms2_tasks = []
        fragmented_count = 0
        if self.scan_to_process is not None:
            # keep growing ROIs if we encounter a new ms1 scan
            self._update_roi(scan)

            self.current_roi_mzs = [roi.mz_list[-1] for roi in self.live_roi]
            self.current_roi_intensities = [roi.intensity_list[-1] for roi in self.live_roi]
            self.current_roi_ids = [roi.id for roi in self.live_roi]

            # FIXME: only the 'scans' mode seems to work on the real mass spec (IAPI), why??
            if self.length_units == "scans":
                self.current_roi_length = np.array([roi.n for roi in self.live_roi])
            else:
                self.current_roi_length = np.array([roi.length_in_seconds for roi in self.live_roi])

            rt = self.scan_to_process.rt

            # loop over points in decreasing score
            scores = self._get_scores()
            idx = np.argsort(scores)[::-1]

            done_ms1 = False

            for i in idx:
                mz = self.current_roi_mzs[i]
                intensity = self.current_roi_intensities[i]
                roi_id = self.current_roi_ids[i]

                # stopping criteria is done based on the scores
                if scores[i] <= 0:
                    logger.debug('Time %f Top-%d ions have been selected' % (rt, self.N))
                    break

                # updated fragmented list and times
                self.live_roi_fragmented[i] = True
                self.live_roi_last_rt[i] = rt

                # create a new ms2 scan parameter to be sent to the mass spec
                precursor_scan_id = self.scan_to_process.scan_id
                dda_scan_params = self.get_ms2_scan_params(mz, intensity, precursor_scan_id, self.isolation_width,
                                                           self.mz_tol, self.rt_tol)
                new_tasks.append(dda_scan_params)
                ms2_tasks.append(dda_scan_params)
                fragmented_count += 1
                self.current_task_id += 1
                self.frag_roi_dicts.append({'scan_id': self.current_task_id, 'roi_id': roi_id,
                                            'precursor_intensity': intensity})

                # add an ms1 here
                if fragmented_count == self.N - self.ms1_shift:
                    ms1_scan_params = self.get_ms1_scan_params()
                    self.current_task_id += 1
                    self.next_processed_scan_id = self.current_task_id
                    logger.debug('Created the next processed scan %d' % (self.next_processed_scan_id))

                    new_tasks.append(ms1_scan_params)
                    done_ms1 = True

            # if no ms1 has been added, then add at the end
            # if fragmented_count < self.N - self.ms1_shift:
            if not done_ms1:
                ms1_scan_params = self.get_ms1_scan_params()
                self.current_task_id += 1
                self.next_processed_scan_id = self.current_task_id
                logger.debug('Created the next processed scan %d' % (self.next_processed_scan_id))
                new_tasks.append(ms1_scan_params)

            # create temp exclusion items
            # tasks = new_tasks[
            #         min(self.N - self.ms1_shift + 1, len(new_tasks)):max(self.N - self.ms1_shift + 1, len(new_tasks))]
            # self.temp_exclusion_list = self._update_temp_exclusion_list(tasks)
            self.temp_exclusion_list = self._update_temp_exclusion_list(ms2_tasks)

            # set this ms1 scan as has been processed
            self.scan_to_process = None
        if scan.ms_level == 2:  # add ms2 scans to Rois
            self.add_scan_to_roi(scan)
        return new_tasks

    def update_state_after_scan(self, last_scan):
        pass

    def add_scan_to_roi(self, scan):
        frag_event_ids = np.array([event['scan_id'] for event in self.frag_roi_dicts])
        which_event = np.where(frag_event_ids == scan.scan_id)[0]
        live_roi_ids = np.array([roi.id for roi in self.live_roi])
        which_roi = np.where(live_roi_ids == self.frag_roi_dicts[which_event[0]]['roi_id'])[0]
        if len(which_roi) > 0:
            self.live_roi[which_roi[0]].add_fragmentation_event(
                scan, self.frag_roi_dicts[which_event[0]]['precursor_intensity'])
            del self.frag_roi_dicts[which_event[0]]
        else:
            pass  # hopefully shouldnt happen



    def _update_roi(self, new_scan):
        if new_scan.ms_level == 1:
            order = np.argsort(self.live_roi)
            self.live_roi.sort()
            self.live_roi_fragmented = np.array(self.live_roi_fragmented)[order].tolist()
            self.live_roi_last_rt = np.array(self.live_roi_last_rt)[order].tolist()
            current_ms1_scan_rt = new_scan.rt
            not_grew = set(self.live_roi)
            for idx in range(len(new_scan.intensities)):
                intensity = new_scan.intensities[idx]
                mz = new_scan.mzs[idx]
                if intensity >= self.min_roi_intensity:
                    match_roi = match(Roi(mz, 0, 0), self.live_roi, self.mz_tol, mz_units=self.mz_units)
                    if match_roi:
                        match_roi.add(mz, current_ms1_scan_rt, intensity)
                        if match_roi in not_grew:
                            not_grew.remove(match_roi)
                    else:
                        new_roi = Roi(mz, current_ms1_scan_rt, intensity, self.roi_id_counter)
                        self.roi_id_counter += 1
                        bisect.insort_right(self.live_roi, new_roi)
                        self.live_roi_fragmented.insert(self.live_roi.index(new_roi), False)
                        self.live_roi_last_rt.insert(self.live_roi.index(new_roi), None)

            for roi in not_grew:
                if self.length_units == "scans":
                    if roi.n >= self.min_roi_length:
                        self.dead_roi.append(roi)
                    else:
                        self.junk_roi.append(roi)
                else:
                    if roi.length_in_seconds >= self.min_roi_length:
                        self.dead_roi.append(roi)
                    else:
                        self.junk_roi.append(roi)

                pos = self.live_roi.index(roi)
                del self.live_roi[pos]
                del self.live_roi_fragmented[pos]
                del self.live_roi_last_rt[pos]

    def _get_scores(self):
        NotImplementedError()
        
    def _score_filters(self):
        intensity_filter = (np.array(self.current_roi_intensities) > self.min_ms1_intensity)
        time_filter = np.logical_not(self.scan_to_process.rt - np.array(self.live_roi_last_rt, dtype=np.double) < self.rt_tol) #Handles None values by converting to NaN for which all comparisons return 0
        length_filter = (self.current_roi_length >= self.min_roi_length_for_fragmentation)
        return intensity_filter * time_filter * length_filter

    def _get_dda_scores(self):
        return np.log(self.current_roi_intensities) * self._score_filters()

    def _get_top_N_scores(self, scores):
        if len(scores) > self.N:  # number of fragmentation events filter
            scores[scores.argsort()[:(len(scores) - self.N)]] = 0
        return scores


class SmartRoiController(RoiController):
    def __init__(self, ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                 min_roi_length, N, rt_tol=10, min_roi_length_for_fragmentation=1,
                 reset_length_seconds=100, intensity_increase_factor=2, length_units="scans",
                 drop_perc=0.01, ms1_shift=0, params=None):
        super().__init__(ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                         min_roi_length, N, rt_tol=rt_tol,
                         min_roi_length_for_fragmentation=min_roi_length_for_fragmentation,
                         length_units=length_units, ms1_shift=ms1_shift,
                         params=params)
        self.reset_length_seconds = reset_length_seconds
        self.intensity_increase_factor = intensity_increase_factor
        self.drop_perc = drop_perc

    def _process_scan(self, scan):

        # if there's a previous ms1 scan to process
        new_tasks = []
        fragmented_count = 0
        if self.scan_to_process is not None:

            # keep growing ROIs if we encounter a new ms1 scan
            self._update_roi(scan)
            logger.debug("Updated rois, currently %d rois" % (len(self.live_roi)))
            self.current_roi_mzs = [roi.mz_list[-1] for roi in self.live_roi]
            self.current_roi_intensities = [roi.get_max_intensity() for roi in self.live_roi]
            self.current_rt = self.scan_to_process.rt

            # FIXME: only the 'scans' mode seems to work on the real mass spec (IAPI), why??
            if self.length_units == "scans":
                self.current_roi_length = np.array([roi.n for roi in self.live_roi])
            else:
                self.current_roi_length = np.array([roi.length_in_seconds for roi in self.live_roi])

            # loop over points in decreasing score
            scores = self._get_scores()
            idx = np.argsort(scores)[::-1]

            done_ms1 = False
            ms2_tasks = []

            for i in idx:
                mz = self.current_roi_mzs[i]
                intensity = self.current_roi_intensities[i]

                # stopping criteria is done based on the scores
                if scores[i] <= 0:
                    logger.debug('Time %f, %d ions have been selected' % (self.current_rt, len(ms2_tasks)))
                    break

                # updated fragmented list and times
                self.live_roi_fragmented[i] = True
                self.live_roi_last_rt[i] = self.current_rt

                # create a new ms2 scan parameter to be sent to the mass spec
                precursor_scan_id = self.scan_to_process.scan_id
                dda_scan_params = self.get_ms2_scan_params(mz, intensity, precursor_scan_id, self.isolation_width,
                                                           self.mz_tol, self.rt_tol)
                new_tasks.append(dda_scan_params)
                ms2_tasks.append(dda_scan_params)
                self.live_roi[i].fragmented()
                fragmented_count += 1
                self.current_task_id += 1

                # add an ms1 here
                if fragmented_count == self.N - self.ms1_shift:
                    ms1_scan_params = self.get_ms1_scan_params()
                    self.current_task_id += 1
                    self.next_processed_scan_id = self.current_task_id
                    logger.debug('Created the next processed scan %d' % (self.next_processed_scan_id))

                    new_tasks.append(ms1_scan_params)
                    done_ms1 = True

            # if no ms1 has been added, then add at the end
            # if fragmented_count < self.N - self.ms1_shift:
            if not done_ms1:
                ms1_scan_params = self.get_ms1_scan_params()
                self.current_task_id += 1
                self.next_processed_scan_id = self.current_task_id
                logger.debug('Created the next processed scan %d' % (self.next_processed_scan_id))

                new_tasks.append(ms1_scan_params)

            # create temp exclusion items
            self.temp_exclusion_list = self._update_temp_exclusion_list(ms2_tasks)

            # set this ms1 scan as has been processed
            self.scan_to_process = None
        return new_tasks

    def _update_roi(self, new_scan):
        if new_scan.ms_level == 1:
            order = np.argsort(self.live_roi)
            self.live_roi.sort()
            self.live_roi_fragmented = np.array(self.live_roi_fragmented)[order].tolist()
            self.live_roi_last_rt = np.array(self.live_roi_last_rt)[order].tolist()
            current_ms1_scan_rt = new_scan.rt
            not_grew = set(self.live_roi)
            for idx in range(len(new_scan.intensities)):
                intensity = new_scan.intensities[idx]
                mz = new_scan.mzs[idx]
                if intensity >= self.min_roi_intensity:
                    match_roi = match(SmartRoi(mz, 0, 0, self.min_roi_length_for_fragmentation,
                                               self.reset_length_seconds, self.intensity_increase_factor, self.rt_tol),
                                      self.live_roi, self.mz_tol, mz_units=self.mz_units)
                    if match_roi:
                        match_roi.add(mz, current_ms1_scan_rt, intensity)
                        if match_roi in not_grew:
                            not_grew.remove(match_roi)
                    else:
                        new_roi = SmartRoi(mz, current_ms1_scan_rt, intensity, self.min_roi_length_for_fragmentation,
                                           self.reset_length_seconds, self.intensity_increase_factor, self.rt_tol,
                                           drop_perc=self.drop_perc)
                        bisect.insort_right(self.live_roi, new_roi)
                        self.live_roi_fragmented.insert(self.live_roi.index(new_roi), False)
                        self.live_roi_last_rt.insert(self.live_roi.index(new_roi), None)

            for roi in not_grew:
                if self.length_units == "scans":
                    if roi.n >= self.min_roi_length:
                        self.dead_roi.append(roi)
                    else:
                        self.junk_roi.append(roi)
                else:
                    if roi.length_in_seconds >= self.min_roi_length:
                        self.dead_roi.append(roi)
                    else:
                        self.junk_roi.append(roi)

                pos = self.live_roi.index(roi)
                del self.live_roi[pos]
                del self.live_roi_fragmented[pos]
                del self.live_roi_last_rt[pos]

    def _get_dda_scores(self):
        scores = np.log(self.current_roi_intensities)  # log intensities
        scores *= (np.array(self.current_roi_intensities) > self.min_ms1_intensity)  # intensity filter
        scores *= ([roi.get_can_fragment() for roi in self.live_roi])
        return scores


########################################################################################################################
# Extended ROI Controllers
########################################################################################################################


class TopN_SmartRoiController(SmartRoiController):
    def __init__(self, ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                 min_roi_length, N=None, rt_tol=10, min_roi_length_for_fragmentation=1,
                 reset_length_seconds=100, intensity_increase_factor=2, length_units="scans", drop_perc=0.01,
                 ms1_shift=0, params=None):
        super().__init__(ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                         min_roi_length, N, rt_tol=rt_tol,
                         min_roi_length_for_fragmentation=min_roi_length_for_fragmentation,
                         reset_length_seconds=reset_length_seconds, intensity_increase_factor=intensity_increase_factor,
                         length_units=length_units, drop_perc=drop_perc, ms1_shift=ms1_shift,
                         params=params)

    def _get_scores(self):
        initial_scores = self._get_dda_scores()
        scores = self._get_top_N_scores(initial_scores)
        return scores


class TopN_RoiController(RoiController):
    def __init__(self, ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                 min_roi_length, N=None, rt_tol=10, min_roi_length_for_fragmentation=1, length_units="scans",
                 ms1_shift=0, params=None):
        super().__init__(ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                         min_roi_length, N, rt_tol=rt_tol,
                         min_roi_length_for_fragmentation=min_roi_length_for_fragmentation,
                         length_units=length_units, ms1_shift=ms1_shift, params=params)

    def _get_scores(self):
        initial_scores = self._get_dda_scores()
        scores = self._get_top_N_scores(initial_scores)
        return scores


class TopNBoxRoiController(RoiController):
    def __init__(self, ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                 min_roi_length, boxes_params=None, boxes=None, boxes_intensity=None, N=None, rt_tol=10,
                 min_roi_length_for_fragmentation=1, length_units="scans", ms1_shift=0, params=None,
                 box_min_rt_width=0.01, box_min_mz_width=0.01):

        self.boxes_params = boxes_params
        self.boxes = boxes
        self.boxes_intensity = boxes_intensity  # the intensity the boxes have been fragmented at before
        self.box_min_rt_width = box_min_rt_width
        self.box_min_mz_width = box_min_mz_width
        super().__init__(ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                         min_roi_length, N, rt_tol=rt_tol,
                         min_roi_length_for_fragmentation=min_roi_length_for_fragmentation,
                         length_units=length_units, ms1_shift=ms1_shift, params=params)

    def _get_scores(self):
        if self.boxes is not None:
            # calculate dda stuff
            log_intensities = np.log(self.current_roi_intensities)
            intensity_filter = (np.array(self.current_roi_intensities) > self.min_ms1_intensity)
            time_filter = (1 - np.array(self.live_roi_fragmented).astype(int))
            time_filter[time_filter == 0] = (
                    (self.scan_to_process.rt - np.array(self.live_roi_last_rt)[time_filter == 0]) > self.rt_tol)
            # calculate overlap stuff
            initial_scores = []
            copy_boxes = deepcopy(self.boxes)
            for box in copy_boxes:
                box.pt2.x = min(box.pt2.x, max(self.last_ms1_rt, box.pt1.x))
            prev_intensity = np.maximum(np.log(np.array(self.boxes_intensity)), [0 for i in self.boxes_intensity])
            box_fragmented = (np.array(self.boxes_intensity) == 0) * 1
            for i in range(len(log_intensities)):
                overlaps = np.array(self.live_roi[i].get_boxes_overlap(copy_boxes, self.box_min_rt_width,
                                                                       self.box_min_mz_width))
                # new peaks not in list of boxes
                new_peaks_score = max(0, (1-sum(overlaps))) * log_intensities[i]
                # previously fragmented peaks
                old_peaks_score1 = sum(overlaps * (log_intensities[i] - prev_intensity) * (1 - box_fragmented))
                # peaks seen before, but not fragmented
                old_peaks_score2 = sum(overlaps * log_intensities[i] * box_fragmented)
                # get the score
                score = self.boxes_params['theta1'] * new_peaks_score
                score += self.boxes_params['theta2'] * old_peaks_score1
                score += self.boxes_params['theta3'] * old_peaks_score2
                score *= time_filter[i]
                score *= intensity_filter  # check intensity meets minimal requirement
                score *= (score > self.boxes_params['min_score']) # check meets min score
                initial_scores.append(score[0])
            initial_scores = np.array(initial_scores)
        else:
            initial_scores = self._get_dda_scores()

        scores = self._get_top_N_scores(initial_scores)
        return scores


class TopNBoxModelRoiController(TopNBoxRoiController):
    def __init__(self, ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                 min_roi_length, boxes_params=None, boxes=None, boxes_intensity=None, boxes_p_values=None, N=None,
                 rt_tol=10, min_roi_length_for_fragmentation=1, length_units="scans", ms1_shift=0, params=None,
                 box_min_rt_width=0.01, box_min_mz_width=0.01):
        self.boxes_p_values = boxes_p_values
        super().__init__(ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
                 min_roi_length, boxes_params, boxes, boxes_intensity, N, rt_tol,
                 min_roi_length_for_fragmentation, length_units, ms1_shift, params,
                 box_min_rt_width, box_min_mz_width)

    def _get_scores(self):
        if self.boxes is not None:
            # calculate dda stuff
            log_intensities = np.log(self.current_roi_intensities)
            intensity_filter = (np.array(self.current_roi_intensities) > self.min_ms1_intensity)
            time_filter = (1 - np.array(self.live_roi_fragmented).astype(int))
            time_filter[time_filter == 0] = (
                    (self.scan_to_process.rt - np.array(self.live_roi_last_rt)[time_filter == 0]) > self.rt_tol)
            # calculate overlap stuff
            initial_scores = []
            copy_boxes = deepcopy(self.boxes)
            for box in copy_boxes:
                box.pt2.x = min(box.pt2.x, max(self.last_ms1_rt, box.pt1.x))
            prev_intensity = np.maximum(np.log(np.array(self.boxes_intensity)), [0 for i in self.boxes_intensity])
            # p value stuff
            if self.boxes_p_values is not None:
                p_value_scores = self.boxes_params['theta2'] * (1 + (1 - np.array(self.boxes_p_values)))
            for i in range(len(log_intensities)):
                overlaps = np.array(self.live_roi[i].get_boxes_overlap(copy_boxes, self.box_min_rt_width,
                                                                       self.box_min_mz_width))
                score = max(0, (1-sum(overlaps))) * log_intensities[i] * time_filter[i]  # new peaks
                old_peaks_score = self.boxes_params['theta1'] * sum(overlaps * (log_intensities[i] - prev_intensity))  # old peaks
                score += old_peaks_score * time_filter[i]
                if self.boxes_p_values is not None:
                    score += self.boxes_params['theta2'] * sum(overlaps * p_value_scores)
                score *= intensity_filter  # check intensity meets minimal requirement
                score *= (score > self.boxes_params['min_score']) # check meets min score
                initial_scores.append(score[0])
            initial_scores = np.array(initial_scores)
        else:
            initial_scores = self._get_dda_scores()

        scores = self._get_top_N_scores(initial_scores)
        return scores


# class TopNBoxModelRoiController(TopNBoxRoiController):
#     def __init__(self, ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
#                  min_roi_length, boxes_params=None, boxes=None, boxes_intensity=None, boxes_p_values=None, N=None,
#                  rt_tol=10, min_roi_length_for_fragmentation=1, length_units="scans", ms1_shift=0, params=None,
#                  box_min_rt_width=0.01, box_min_mz_width=0.01):
#         self.boxes_p_values = boxes_p_values
#         super().__init__(ionisation_mode, isolation_width, mz_tol, min_ms1_intensity, min_roi_intensity,
#                  min_roi_length, boxes_params, boxes, boxes_intensity, N, rt_tol,
#                  min_roi_length_for_fragmentation, length_units, ms1_shift, params,
#                  box_min_rt_width, box_min_mz_width)
#
#     def _get_scores(self):
#         dda_scores = self._get_dda_scores()
#         if self.boxes is not None:
#             overlap_scores = []
#             for i in range(len(dda_scores)):
#                 overlaps = np.array(self.live_roi[i].get_boxes_overlap(self.boxes, self.box_min_rt_width,
#                                                                        self.box_min_mz_width))
#                 prev_intensity = np.maximum(np.log(np.array(self.boxes_intensity)),[0 for i in self.boxes_intensity])
#                 intensity_differences = np.log(np.array(self.live_roi[i].intensity_list[-1])) - prev_intensity
#
#                 overlap_scores.append(sum((intensity_differences * overlaps)))
#
#             if self.boxes_p_values is not None:
#                 p_value_scores = self.boxes_params['theta2'] * (1 + (1 - np.array(self.boxes_p_values)))
#                 initial_scores = dda_scores + (
#                         np.array(overlap_scores) * p_value_scores * self.boxes_params['theta1'] * (dda_scores > 0) * 1)
#             else:
#                 initial_scores = dda_scores + np.array(overlap_scores) * self.boxes_params['theta1'] * (
#                             dda_scores > 0) * 1
#         else:
#             initial_scores = dda_scores
#         # self.boxes_intensities plus need to take into account current box intensity
#         scores = self._get_top_N_scores(initial_scores)
#         return scores


########################################################################################################################
# Other Functions
########################################################################################################################


def get_peak_status(mzs, rt, boxes, scores, model_scores=None, box_mz_tol=10):
    if model_scores is not None:
        list1 = list(filter(lambda x: x[0].rt_range_in_seconds[0] <= rt <= x[0].rt_range_in_seconds[1],
                            zip(boxes, scores, model_scores)))
        model_score_status = []
    else:
        list1 = list(filter(lambda x: x[0].rt_range_in_seconds[0] <= rt <= x[0].rt_range_in_seconds[1],
                            zip(boxes, scores)))
        model_score_status = None
    peak_status = []
    for mz in mzs:
        list2 = list(filter(lambda x: x[0].mz_range[0] * (1 - box_mz_tol / 1e6) <= mz <=
                                      x[0].mz_range[1] * (1 + box_mz_tol / 1e6), list1))
        if list2 == []:
            peak_status.append(-1)
            if model_scores is not None:
                model_score_status.append(1)
        else:
            scores = [x[1] for x in list2]
            peak_status.append(min(scores))
            if model_scores is not None:
                m_scores = [x[2] for x in list2]
                model_score_status.append(max(m_scores))
    return peak_status, model_score_status


def get_box_intensity(mzml_file, boxes):
    intensities = [0 for i in range(len(boxes))]
    mzs = [None for i in range(len(boxes))]
    box_ids = range(len(boxes))
    mz_file = MZMLFile(mzml_file)
    for scan in mz_file.scans:
        if scan.ms_level == 2:
            continue
        rt = scan.rt_in_seconds
        zipped_boxes = list(
            filter(lambda x: x[0].rt_range_in_seconds[0] <= rt <= x[0].rt_range_in_seconds[1], zip(boxes, box_ids)))
        if not zipped_boxes:
            continue
        for mzint in scan.peaks:
            mz = mzint[0]
            sub_boxes = list(filter(lambda x: x[0].mz_range[0] <= mz <= x[0].mz_range[1], zipped_boxes))
            if not sub_boxes:
                continue
            for box in sub_boxes:
                intensity = mzint[1]
                if intensity > intensities[box[1]]:
                    intensities[box[1]] = intensity
                    mzs[box[1]] = mz
    return intensities, mzs
