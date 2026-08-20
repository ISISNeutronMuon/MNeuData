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

    REPO_DATA_DIR = Path() / "data"
    RUN_SUMMARY_DIR = Path(os.environ["RUN_SUMMARY_DIR"])

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
                j.number_spectra,
                j.number_time_channels,
                n.total_detector_mcounts AS nxs_detector_mcounts,
                n.total_monitor_mcounts AS nxs_monitor_mcounts,
                round(j.raw_frames/j.duration, 1) as framerate_hz
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
        -- select * from run_summary where beamline = 'WISH' and event_mode > 0
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
                FALSE AS endeavour,
                run_number,
                framerate_hz,
                (nxs_detector_mcounts / good_frames) AS detector_mevents_per_frame,
                (nxs_monitor_mcounts / good_frames) AS monitor_mevents_per_frame
            FROM
                run_summary r

            UNION

            SELECT
                e.beamline,
                TRUE AS endeavour,
                NULL as run_number,
                r.framerate_hz,
                (nxs_detector_mcounts / good_frames) * e.detector_rate_sf AS detector_mevents_per_frame,
                (nxs_monitor_mcounts / good_frames) * e.monitor_rate_sf AS monitor_mevents_per_frame,
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

    # legacy fields
    #event_frame_number_bits = 32
    #event_time_bins = 32
    return (
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
        nxs_per_event_compression_ratio,
        nxs_per_frame_compression_ratio,
    )


@app.cell
def _(
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
    nxs_per_event_compression_ratio,
    nxs_per_frame_compression_ratio,
):
    _df = mo.sql(
        f"""
        -- We assume 1 ev44 message holds 1 frame
        CREATE OR REPLACE MACRO to_mbits_sec (framerate_hz, mevts_per_frame) AS framerate_hz * (
            (({ev44_source_name_bits + ev44_message_id_bits + ev44_ref_time_bits + ev44_ref_time_index_bits}) + 1e6 * mevts_per_frame * ({ev44_pixel_id_bits + ev44_tof_bits})) / 1e6
        );

        CREATE OR REPLACE MACRO nexus_mbytes_hr (framerate_hz, mevts_per_frame) AS (
            (
                3600 * framerate_hz * (
                    ({nxs_event_index_bits} + {nxs_event_time_zero_bits}) / {nxs_per_frame_compression_ratio} + 1e6 * mevts_per_frame * ({nxs_event_id_bits} + {nxs_event_time_offset_bits}) / {nxs_per_event_compression_ratio}
                )
            ) / 8 / 1024 ** 2
        );

        CREATE OR REPLACE TABLE data_rates_per_run AS (
            SELECT
                beamline,
                endeavour,
                TO_MBITS_SEC (
                    framerate_hz,
                    detector_mevents_per_frame
                ) AS detector_mbits_sec,
                TO_MBITS_SEC (framerate_hz, monitor_mevents_per_frame) AS monitor_mbits_sec,
                NEXUS_MBYTES_HR(framerate_hz, detector_mevents_per_frame) / 1024 AS nxs_detector_gbytes_hr,
                NEXUS_MBYTES_HR(framerate_hz, monitor_mevents_per_frame) / 1024 AS nxs_monitor_gbytes_hr,
                run_number,
                -- cycle_name,
                -- framerate_hz,
            FROM
                event_counts_per_run
        );

        -- select * from data_rates_per_run where beamline = 'WISH';
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
                ROUND(max(detector_mbits_sec + monitor_mbits_sec), 4) as max_mbits_sec,
                ROUND(max(nxs_detector_gbytes_hr + nxs_monitor_gbytes_hr), 4) as max_nxs_gbytes_hr,
            FROM
                data_rates_per_run d
            GROUP BY
                beamline, endeavour
        )
        SELECT
            ds.beamline,
            max_mbits_sec,
            max_nxs_gbytes_hr,
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
