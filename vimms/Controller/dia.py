import os
from loguru import logger
import csv

from vimms.Common import DEFAULT_MS1_AGC_TARGET, DEFAULT_MS1_MAXIT, DEFAULT_MS1_COLLISION_ENERGY, \
    DEFAULT_MS1_ORBITRAP_RESOLUTION, DEFAULT_MS2_AGC_TARGET, DEFAULT_MS2_MAXIT, DEFAULT_MS2_COLLISION_ENERGY, \
    DEFAULT_MS2_ORBITRAP_RESOLUTION, DEFAULT_MS2_ISOLATION_MODE, DEFAULT_MS2_ACTIVATION_TYPE, \
    DEFAULT_MS2_MASS_ANALYSER, create_if_not_exist
from vimms.Controller import Controller
from vimms.MassSpec import ScanParameters


class AIF(Controller):
    def __init__(self, min_mz, max_mz, params=None):
        super().__init__(params=params)
        self.min_mz = min_mz  # scan from this mz
        self.max_mz = max_mz  # scan to this mz
        self.scan_number = self.initial_scan_id


    def write_msdial_experiment_file(self, filename):
        raise NotImplementedError()
    
    # method required by super-class
    def update_state_after_scan(self, last_scan):
        pass

    def _process_scan(self, scan):
        # method called when a scan arrives that requires action
        # normally means that we should schedule some more
        # in DIA we don't need to actually look at the peaks
        # in the scan, just schedule the next block

        # For all ions fragmentation, when we receive the last scan of the previous block
        #  we make a new block
        # each block is an MS1 scan followed by an MS2 scan where the MS2 fragmens everything
        scans = []

        if self.scan_to_process is not None:
            # make the MS2 scan
            dda_scan_params = ScanParameters()
            dda_scan_params.set(ScanParameters.MS_LEVEL, 1)
            dda_scan_params.set(ScanParameters.COLLISION_ENERGY, self.params.ms2_collision_energy)
            dda_scan_params.set(ScanParameters.AGC_TARGET, self.params.ms2_agc_target)
            dda_scan_params.set(ScanParameters.MAX_IT, self.params.ms2_max_it)
            dda_scan_params.set(ScanParameters.ORBITRAP_RESOLUTION, self.params.ms2_orbitrap_resolution)
            dda_scan_params.set(ScanParameters.PRECURSOR_MZ, 0.5 * (self.max_mz + self.min_mz))
            dda_scan_params.set(ScanParameters.FIRST_MASS, self.min_mz)
            dda_scan_params.set(ScanParameters.LAST_MASS, self.max_mz)

            scans.append(dda_scan_params)
            self.scan_number += 1  # increase every time we make a scan

            # make the MS1 scan
            task = self.environment.get_default_scan_params(agc_target=self.params.ms1_agc_target,
                                                            max_it=self.params.ms1_max_it,
                                                            collision_energy=self.params.ms1_collision_energy,
                                                            orbitrap_resolution=self.params.ms1_orbitrap_resolution)
            task.set(ScanParameters.FIRST_MASS, self.min_mz)
            task.set(ScanParameters.LAST_MASS, self.max_mz)
            # task.set(ScanParameters.CURRENT_TOP_N, 10) # time sampling fix see iss18

            scans.append(task)
            self.scan_number += 1
            self.next_processed_scan_id = self.scan_number

            # set this ms1 scan as has been processed
            self.scan_to_process = None

        return scans


class SWATH(Controller):
    def __init__(self, min_mz, max_mz,
                 width, scan_overlap=0,
                 params=None):
        super().__init__(params=params)
        self.width = width
        self.scan_overlap = scan_overlap
        self.min_mz = min_mz  # scan from this mz
        self.max_mz = max_mz  # scan to this mz

        self.scan_number = self.initial_scan_id
        self.exp_info = []  # experimental information - isolation windows

    def write_msdial_experiment_file(self, filename):
        heads = ['Experiment','MS Type','Min m/z','Max m/z']
        start_mz, stop_mz = self._get_start_stop()
        ms1_mz_range = self.params.default_ms1_scan_window
        ms1_row = ['0', 'SCAN', ms1_mz_range[0], ms1_mz_range[1]]
        swath_rows = []
        for i,start in enumerate(start_mz):
            stop = stop_mz[i]
            new_row = [i+1, 'SWATH', start, stop]
            swath_rows.append(new_row)


        out_dir = os.path.dirname(filename)
        create_if_not_exist(out_dir)

        with open(filename, 'w') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(heads)
            writer.writerow(ms1_row)
            for row in swath_rows:
                writer.writerow(row)


    def _get_start_stop(self):
        start = self.min_mz
        start_mz = []
        stop_mz = []
        while start < self.max_mz:
            start_mz.append(start)
            stop_mz.append(start + self.width)
            start += self.width - self.scan_overlap
        return start_mz, stop_mz

    def update_state_after_scan(self, last_scan):
        pass

    def _process_scan(self, scan):
        new_tasks = []
        if self.scan_to_process is not None:

            precursor_scan_id = self.scan_to_process.scan_id

            start_mz, stop_mz = self._get_start_stop()

            isolation_width = self.width

            precursor_mz_list = []
            for i, start in enumerate(start_mz):
                precursor_mz = (stop_mz[i] + start) / 2.
                precursor_mz_list.append(precursor_mz)

            mz_tol = 10  # not used
            rt_tol = 15  # these are not used
            for mz in precursor_mz_list:
                dda_scan_params = self.get_ms2_scan_params(mz, 0, precursor_scan_id, isolation_width, mz_tol, rt_tol)
                new_tasks.append(dda_scan_params)  # push this dda scan to the mass spec queue

            # make the MS1 scan
            task = self.get_ms1_scan_params()
            new_tasks.append(task)

            self.scan_number += len(precursor_mz_list) + 1
            self.next_processed_scan_id = self.scan_number
        return new_tasks
