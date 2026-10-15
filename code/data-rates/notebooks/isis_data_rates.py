import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path
    import dotenv
    import marimo as mo

    dotenv.load_dotenv()

    # Data
    REPO_DATA_DIR = Path() / "data"
    RUN_SUMMARY_DIR = Path(os.environ["RUN_SUMMARY_DIR"])

    # Constants
    print(f"Loading run summaries from '{RUN_SUMMARY_DIR}'")
    return REPO_DATA_DIR, RUN_SUMMARY_DIR, mo


@app.cell
def _(REPO_DATA_DIR, mo):
    _df = mo.sql(
        f"""
        -- Repo, static data
        CREATE OR REPLACE TABLE beamline AS (
            SELECT
                beamline,
                target_station
            FROM
                read_json('{REPO_DATA_DIR}/beamline.json')
        );
        """
    )
    return


@app.cell
def _(RUN_SUMMARY_DIR, mo):
    _df = mo.sql(
        f"""
        -- Run data tables
        -- Exclude runs where the total number of events recorded by the DAE counter is less
        -- than recorded in the files.
        CREATE OR REPLACE TABLE run_summary AS (
            SELECT
                j.beamline,
                j."cycle" AS cycle_name,
                j.run_number,
                j.event_mode,
                j.frame_sync,
                j.raw_frames,
                j.good_frames,
                j.duration,
                j.total_mevents as journal_total_mevents,
                j.number_periods,
                j.number_spectra,
                j.number_time_channels[1] AS number_of_time_channels,
                n.number_monitors,
                n.total_detector_mcounts AS nxs_detector_mcounts,
                n.total_monitor_mcounts AS nxs_monitor_mcounts,
                ROUND(n.file_size_bytes / 1000**2, 4) AS nxs_file_size_mbytes,
                ROUND(j.raw_frames/j.duration, 1) as framerate_hz
            FROM
                read_parquet('{RUN_SUMMARY_DIR}/*_journal.parquet') j
            JOIN
                (SELECT * FROM read_parquet('{RUN_SUMMARY_DIR}/*_nexus.parquet')) n ON
                    j.beamline = n.beamline AND j."cycle" = n."cycle" AND j.run_number = n.run_number
            WHERE
                frame_sync NOT ILIKE '%internal%'
                AND duration > 0.0
                AND raw_frames > 1
                AND good_frames > 1
                AND journal_total_mevents > 0
                AND journal_total_mevents >= (nxs_detector_mcounts + nxs_monitor_mcounts)
        );
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- debugging cell
        -- select
        --     *
        -- from
        --     run_summary
        -- where
        --     beamline = 'LET'
        --     and event_mode > 0
        """
    )
    return


@app.cell
def _(REPO_DATA_DIR, mo, run_summary):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE event_counts_per_run AS (
            SELECT
                beamline,
                cycle_name,
                run_number,
                event_mode,
                duration,
                framerate_hz,
                number_periods,
                number_spectra,
            	number_monitors,
            	number_of_time_channels,
                (nxs_detector_mcounts / good_frames) AS detector_mevents_per_frame,
                (nxs_monitor_mcounts / good_frames) AS monitor_mevents_per_frame,
                nxs_file_size_mbytes,
                FALSE AS endeavour,
            FROM
                run_summary r

            UNION

            SELECT
                e.beamline,
                cycle_name,
                NULL as run_number,
                event_mode,
                duration,
                r.framerate_hz,
                number_periods,
                NULL as number_spectra,
            	number_monitors,
            	number_of_time_channels,
                (nxs_detector_mcounts / good_frames) * e.detector_rate_sf AS detector_mevents_per_frame,
                (nxs_monitor_mcounts / good_frames) * e.monitor_rate_sf AS monitor_mevents_per_frame,
                NULL AS nxs_file_size_mbytes,
                TRUE AS endeavour
            FROM
                run_summary r
            JOIN (SELECT * from READ_JSON('{REPO_DATA_DIR}/endeavour.json')) e ON r.beamline = e.sf_base
        );
        """
    )
    return


@app.cell
def _():
    # ---------------------
    # Event type information
    # Matches ESS ev44 schema:
    # https://github.com/ess-dmsc/streaming-data-types/blob/5fde74d8eb69658073735984acc9465ed10870b1/schemas/ev44_events.fbs
    #
    # Assumptions:
    #   - a single Event44Message per ISIS frame
    #   - source_name assumes a maximum char length=16
    # ---------------------
    ev44_source_name_bits = 16 * 8
    ev44_message_id_bits = 64
    ev44_ref_time_bits = 64  # single frame
    ev44_ref_time_index_bits = 32

    ev44_tof_bits = 32
    ev44_pixel_id_bits = 32

    # ---------------------
    # Diagnostic information
    # ---------------------
    diag_bits = 96

    # ---------------------
    # NeXus information
    # ---------------------
    # Compression numbers were produced by checking a few files and looking at `dataset.nbytes()/dataset.id.get_storage_size()`

    # per frame
    nxs_event_index_bits = 64
    nxs_event_time_zero_bits = 64
    nxs_per_frame_compression_ratio = 2.5

    # per-event
    nxs_event_id_bits = 32
    nxs_event_time_offset_bits = 32
    nxs_per_event_compression_ratio = 1.3

    # histo
    nxs_histo_count_bits = 32
    nxs_histo_tof_bits = 32
    nxs_histo_compression_ratio = 4.5
    return (
        diag_bits,
        ev44_message_id_bits,
        ev44_pixel_id_bits,
        ev44_ref_time_bits,
        ev44_ref_time_index_bits,
        ev44_source_name_bits,
        ev44_tof_bits,
        nxs_event_id_bits,
        nxs_event_index_bits,
        nxs_event_time_offset_bits,
        nxs_event_time_zero_bits,
        nxs_histo_compression_ratio,
        nxs_histo_count_bits,
        nxs_histo_tof_bits,
        nxs_per_event_compression_ratio,
        nxs_per_frame_compression_ratio,
    )


@app.cell
def _(
    diag_bits,
    ev44_message_id_bits,
    ev44_pixel_id_bits,
    ev44_ref_time_bits,
    ev44_ref_time_index_bits,
    ev44_source_name_bits,
    ev44_tof_bits,
    event_counts_per_run,
    mo,
    nxs_event_id_bits,
    nxs_event_index_bits,
    nxs_event_time_offset_bits,
    nxs_event_time_zero_bits,
    nxs_histo_compression_ratio,
    nxs_histo_count_bits,
    nxs_histo_tof_bits,
    nxs_per_event_compression_ratio,
    nxs_per_frame_compression_ratio,
):
    _df = mo.sql(
        f"""
        -- Rates primarily for network bandwidth
        --   We assume 1 ev44 message holds 1 frame
        CREATE OR REPLACE MACRO to_mbits_sec (framerate_hz, mevts_per_frame) AS (
            ROUND(
                framerate_hz * (
                    (
                        {
            ev44_source_name_bits
            + ev44_message_id_bits
            + ev44_ref_time_bits
            + ev44_ref_time_index_bits
        }
                    ) + 1e6 * mevts_per_frame * ({
            ev44_pixel_id_bits + ev44_tof_bits + diag_bits
        })
                ) / 1e6,
                4
            )
        );

        -- Estimate the size of the an NXevent_data group after 1 hour collection
        CREATE OR REPLACE MACRO nxs_event_gbytes_hr (framerate_hz, mevts_per_frame) AS (
            ROUND(
                3600 * framerate_hz * (
                    (
                        {nxs_event_index_bits} + {nxs_event_time_zero_bits}
                    ) / {
            nxs_per_frame_compression_ratio
        } + 1e6 * mevts_per_frame * (
                        {nxs_event_id_bits} + {nxs_event_time_offset_bits}
                    ) / {nxs_per_event_compression_ratio}
                ) / 8 / 1e9,
                4
            )
        );

        -- Estimate the size of an NXdata group for a give data shape
        --   Note: Time channels are shared across the file so only a single copy is accounted for 
        CREATE OR REPLACE MACRO nxs_histo_gbytes (
            number_periods,
            number_spectra,
            number_time_channels
        ) AS (
            ROUND(
                (
                    (
                        number_periods * number_spectra * number_time_channels * {
            nxs_histo_count_bits
        }
                    ) + (number_time_channels + 1) * {nxs_histo_tof_bits}
                ) / 8 / 1e9 / {nxs_histo_compression_ratio},
                4
            )
        );

        ----------------------------------------------------------------------------------------
        CREATE OR REPLACE TABLE data_rates_per_run AS (
            SELECT
                beamline,
                TO_MBITS_SEC (framerate_hz, detector_mevents_per_frame) AS detector_mbits_sec,
                TO_MBITS_SEC (framerate_hz, monitor_mevents_per_frame) AS monitor_mbits_sec,
                NXS_EVENT_GBYTES_HR (framerate_hz, detector_mevents_per_frame) AS nxs_detector_event_gbytes_hr,
                NXS_EVENT_GBYTES_HR (framerate_hz, monitor_mevents_per_frame) AS nxs_monitor_event_gbytes_hr,
                NXS_HISTO_GBYTES (
                    number_periods,
                    (number_spectra + number_monitors),
                    number_of_time_channels
                ) AS nxs_histo_gbytes_calculated,
                duration,
                ROUND(nxs_file_size_mbytes / 1e3, 4) AS nxs_file_size_gbytes_actual,
                run_number,
                event_mode,
                endeavour,
                cycle_name,
                -- framerate_hz,
            FROM
                event_counts_per_run
        );

        select
            cycle_name,
            run_number,
            nxs_file_size_gbytes_actual
        from
            data_rates_per_run
        where
            beamline = 'WISH'
        order by nxs_file_size_gbytes_actual desc
        limit 1


        """
    )
    return


@app.cell
def _(beamline, data_rates_per_run, mo):
    _df = mo.sql(
        f"""
        -- Max rates
        WITH d_stats AS (
          SELECT
                beamline,
                endeavour,
                -- we care about the total rate coming over the network
                ROUND(QUANTILE(detector_mbits_sec, 0.99), 4) as det_p99_mbits_sec,
                ROUND(QUANTILE(monitor_mbits_sec, 0.99), 4) as mon_p99_mbits_sec,
                ROUND(QUANTILE(detector_mbits_sec + monitor_mbits_sec, 0.99), 4) as total_p99_mbits_sec,
                ROUND(QUANTILE(nxs_detector_event_gbytes_hr + nxs_monitor_event_gbytes_hr, 0.999), 4) as p999_nxs_event_gbytes_hr,
                ROUND(QUANTILE(nxs_detector_event_gbytes_hr, 0.999), 4) as p999_nxs_event_mon_histo_gbytes_hr,
                MAX(nxs_file_size_gbytes_actual) as max_nxs_histo_gbytes_actual
            FROM
                data_rates_per_run d
            GROUP BY
                beamline, endeavour
        )
        SELECT
            ds.beamline,
            det_p99_mbits_sec,
            mon_p99_mbits_sec,
            total_p99_mbits_sec,
            p999_nxs_event_gbytes_hr,
            p999_nxs_event_mon_histo_gbytes_hr,
            max_nxs_histo_gbytes_actual,
            CONCAT('TS', b.target_station) as target_station,
            ds.endeavour
        FROM
            d_stats ds
        JOIN beamline b ON ds.beamline = b.beamline
        ORDER BY ds.beamline;
        """
    )
    return


if __name__ == "__main__":
    app.run()
