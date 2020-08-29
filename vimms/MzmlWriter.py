import os

import numpy as np
from psims.mzml.writer import MzMLWriter as PsimsMzMLWriter

from vimms.Common import INITIAL_SCAN_ID, create_if_not_exist, DEFAULT_MS1_SCAN_WINDOW
from vimms.MassSpec import ScanParameters


class MzmlWriter(object):
    """A class to write peak data to mzML file"""

    def __init__(self, analysis_name, scans):
        """
        Initialises the mzML writer class.
        :param analysis_name: Name of the analysis.
        :param scans: A dictionary where key is scan level, value is a list of Scans object for that level.
        :param precursor_information: A dictionary where key is Precursor object, value is a list of ms2 scans only
        """
        self.analysis_name = analysis_name
        self.scans = scans

    def write_mzML(self, out_file):
        # if directory doesn't exist, create it
        out_dir = os.path.dirname(out_file)
        create_if_not_exist(out_dir)

        # start writing mzML here
        with PsimsMzMLWriter(open(out_file, 'wb')) as writer:
            # add default controlled vocabularies
            writer.controlled_vocabularies()

            # write other fields like sample list, software list, etc.
            self._write_info(writer)

            # open the run
            with writer.run(id=self.analysis_name):
                self._write_spectra(writer, self.scans)

                # open chromatogram list sections
                with writer.chromatogram_list(count=1):
                    tic_rts, tic_intensities = self._get_tic_chromatogram(self.scans)
                    writer.write_chromatogram(tic_rts, tic_intensities, id='tic',
                                              chromatogram_type='total ion current chromatogram',
                                              time_unit='second')

        writer.close()

    def _write_info(self, out):
        # check file contains what kind of spectra
        has_ms1_spectrum = 1 in self.scans
        has_msn_spectrum = 1 in self.scans and len(self.scans) > 1
        file_contents = [
            'centroid spectrum'
        ]
        if has_ms1_spectrum:
            file_contents.append('MS1 spectrum')
        if has_msn_spectrum:
            file_contents.append('MSn spectrum')
        out.file_description(
            file_contents=file_contents,
            source_files=[]
        )
        out.sample_list(samples=[])
        out.software_list(software_list={
            'id': 'VMS',
            'version': '1.0.0'
        })
        out.scan_settings_list(scan_settings=[])
        out.instrument_configuration_list(instrument_configurations={
            'id': 'VMS',
            'component_list': []
        })
        out.data_processing_list({'id': 'VMS'})

    def sort_filter(self, all_scans, min_scan_id):
        all_scans = sorted(all_scans, key=lambda x: x.rt)
        all_scans = [x for x in all_scans if x.num_peaks > 0]
        all_scans = list(filter(lambda x: x.scan_id >= min_scan_id, all_scans))

        # FIXME: why do we need to do this???!!
        # add a single peak to empty scans
        # empty = [x for x in all_scans if x.num_peaks == 0]
        # for scan in empty:
        #     scan.mzs = np.array([100.0])
        #     scan.intensities = np.array([1.0])
        #     scan.num_peaks = 1
        return all_scans

    def _write_spectra(self, writer, scans, min_scan_id=INITIAL_SCAN_ID):
        assert len(scans) <= 3  # NOTE: we only support writing up to ms2 scans for now

        # get all scans across different ms_levels and sort them by scan_id
        all_scans = []
        for ms_level in scans:
            all_scans.extend(scans[ms_level])
        all_scans = self.sort_filter(all_scans, min_scan_id)
        spectrum_count = len(all_scans)

        # write scans
        with writer.spectrum_list(count=spectrum_count):
            for scan in all_scans:
                self._write_scan(writer, scan)

    def _write_scan(self, out, scan):
        assert scan.num_peaks > 0
        label = 'MS1 Spectrum' if scan.ms_level == 1 else 'MSn Spectrum'
        precursor_information = None
        if scan.ms_level == 2:
            collision_energy = scan.scan_params.get(ScanParameters.COLLISION_ENERGY)
            activation_type = scan.scan_params.get(ScanParameters.ACTIVATION_TYPE)

            # HACK - to be fixed by iss_110
            # remove the [0] from the next line
            # and properly handle the list of precursor objects
            precursor = scan.scan_params.get(ScanParameters.PRECURSOR_MZ)[0]
            precursor_information = {
                "mz": precursor.precursor_mz,
                "intensity": precursor.precursor_intensity,
                "charge": precursor.precursor_charge,
                "spectrum_reference": precursor.precursor_scan_id,
                "activation": [activation_type, {"collision energy": collision_energy}]
            }
        lowest_observed_mz = min(scan.mzs)
        highest_observed_mz = max(scan.mzs)
        bp_pos = np.argmax(scan.intensities)
        bp_intensity = scan.intensities[bp_pos]
        bp_mz = scan.mzs[bp_pos]
        scan_id = scan.scan_id

        try:
            first_mz = scan.scan_params.get(ScanParameters.FIRST_MASS)
            last_mz = scan.scan_params.get(ScanParameters.LAST_MASS)
        except AttributeError: # if it's a method scan (not a custom scan), there's no scan_params to get first_mz and last_mz
            first_mz, last_mz = DEFAULT_MS1_SCAN_WINDOW

        out.write_spectrum(
            scan.mzs, scan.intensities,
            id=scan_id,
            centroided=True,
            scan_start_time=scan.rt / 60.0,
            scan_window_list=[(first_mz, last_mz)],
            params=[
                {label: ''},
                {'ms level': scan.ms_level},
                {'total ion current': np.sum(scan.intensities)},
                {'lowest observed m/z': lowest_observed_mz},
                {'highest observed m/z': highest_observed_mz},
                # {'base peak m/z', bp_mz},
                # {'base peak intensity', bp_intensity}
            ],
            precursor_information=precursor_information
        )

    def _get_tic_chromatogram(self, scans):
        time_array = []
        intensity_array = []
        for ms1_scan in scans[1]:
            time_array.append(ms1_scan.rt)
            intensity_array.append(np.sum(ms1_scan.intensities))
        time_array = np.array(time_array)
        intensity_array = np.array(intensity_array)
        return time_array, intensity_array
