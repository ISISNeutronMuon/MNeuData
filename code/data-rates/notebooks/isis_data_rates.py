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
        CREATE OR REPLACE TABLE endeavour AS (
            SELECT * from READ_JSON('{REPO_DATA_DIR}/endeavour.json')
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
            JOIN (SELECT * FROM read_parquet('{RUN_SUMMARY_DIR}/*_nexus.parquet')) n ON
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
    mo,
    run_summary,
):
    _df = mo.sql(
        f"""
        -- We assume 1 ev44 message holds 1 frame
        CREATE OR REPLACE MACRO to_mbits_sec (framerate_hz, mevts_per_frame) AS framerate_hz * (
            (({ev44_source_name_bits + ev44_message_id_bits + ev44_ref_time_bits + ev44_ref_time_index_bits}) + 1e6 * mevts_per_frame * ({ev44_pixel_id_bits + ev44_tof_bits})) / 1e6
        );

        CREATE OR REPLACE TABLE data_rates AS (
            SELECT
                beamline,
                run_number,
                cycle_name,
                framerate_hz,
                (nxs_detector_mcounts / good_frames) AS detector_mevents_per_frame,
                (nxs_monitor_mcounts / good_frames) AS monitor_mevents_per_frame,
                TO_MBITS_SEC (
                    framerate_hz,
                    detector_mevents_per_frame
                ) AS detector_mbits_sec,
                TO_MBITS_SEC (framerate_hz, monitor_mevents_per_frame) AS monitor_mbits_sec,
            FROM
                run_summary
        );
        """
    )
    return


@app.cell
def _(
    data_rates,
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
        CREATE OR REPLACE MACRO nexus_mbytes_hr (framerate_hz, mevts_per_frame) AS (
            (
                3600 * framerate_hz * (
                    ({nxs_event_index_bits} + {nxs_event_time_zero_bits}) / {nxs_per_frame_compression_ratio} + 1e6 * mevts_per_frame * ({nxs_event_id_bits} + {nxs_event_time_offset_bits}) / {nxs_per_event_compression_ratio}
                )
            ) / 8 / 1024 ** 2
        );

        CREATE OR REPLACE TABLE data_rates_stats AS (
            SELECT
                beamline,
                round(detector_mbits_sec, 4) as max_det_mbits_sec,
                round(monitor_mbits_sec, 4) as max_mon_mbits_sec,
                round(
                    NEXUS_MBYTES_HR (framerate_hz, detector_mevents_per_frame) / 1024,
                    4
                )  as nxs_detector_gbytes_hr,
                round(
                    NEXUS_MBYTES_HR (framerate_hz, monitor_mevents_per_frame) / 1024,
                    4
                ) as nxs_monitor_gbytes_hr
                -- run_number,
                -- cycle_name,
                -- framerate_hz
            FROM
                (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                beamline
                            ORDER BY
                                detector_mbits_sec DESC
                        ) AS _rn
                    FROM
                        data_rates d
                )
            WHERE
                _rn = 1
        );
        """
    )
    return


@app.cell
def _(data_rates_stats, mo):
    _df = mo.sql(
        f"""
        -- CURRENT SUITE
        select * from data_rates_stats;
        """
    )
    return


@app.cell
def _(data_rates_stats, endeavour, mo):
    _df = mo.sql(
        f"""
        -- ENDEAVOUR
        SELECT
            e.beamline,
            round(d.max_det_mbits_sec * e.detector_rate_sf, 4) AS max_det_mbits_sec,
            round(d.max_mon_mbits_sec * e.monitor_rate_sf, 4) AS max_mon_mbits_sec
        FROM
            data_rates_stats d
        JOIN endeavour e ON d.beamline = e.sf_base;
        """
    )
    return


if __name__ == "__main__":
    app.run()
