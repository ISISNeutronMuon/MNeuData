# ISIS NeXus file

## Common fields

## Histograms

### `detector_1`

_Note: Group may be empty if only monitor data has been recorded._

<!-- prettier-ignore-start -->
| Field name          | Data type | Description                                                                                    |
| ------------------- | --------- | ---------------------------------------------------------------------------------------------- |
| counts              | int-32    | Counts as an array with shape (nperiods, nspectra, ntime_channels). |
| period_index        | int-32    | The period numbers for each period collected. Length=nperiods. |
| spectrum_index      | int-32    | The spectrum numbers for each detector/group of detectors contributing to the spectrum. Length=nspectra |
| time_of_flight      | float-32  | The time-of-flight channel boundaries. Length=ntime_channels + 1. |
<!-- prettier-ignore-end -->

### `monitor_N`

A separate group for each monitor. Each has the same files as `detector_1` except `counts` is renamed `data` and there is an additional field:

<!-- prettier-ignore-start -->
| Field name          | Data type | Description                                                                                    |
| ------------------- | --------- | ---------------------------------------------------------------------------------------------- |
| monitor_number      | int-32    | Incrementing number for each monitor group |
<!-- prettier-ignore-end -->

## Events

### `detector_1_events`

_Note: Group may be empty if only monitor data has been recorded._

The following entries are the minimum required to reconstruct the event information:

<!-- prettier-ignore-start -->
| Field name          | Data type | Description                                                                                    |
| ------------------- | --------- | ---------------------------------------------------------------------------------------------- |
| `event_id`          | int-32    | The detector ID assigned to a registered event.                                                |
| `event_index`       | int-64    | For each frame, defines the index of the first event in `event_id` that belongs to that frame. |
| `event_time_offset` | float-32  | The event time-of-flight defined as an array of offsets from frame start (`event_time_zero`).  |
| `event_time_zero`   | float-64  | The start of each frame defined as an array of offsets, in seconds, from run `start_time`.     |
| `total_counts`      | int-64    | The total number of events recorded by all detector pixels. Matches Length(`event_id`).        |
<!-- prettier-ignore-end -->

The following additional entries appear in ISIS event files to deal with legacy issues with electronics:

<!-- prettier-ignore-start -->
| Field name           | Data type | Description |
| -------------------- | --------- | ----------- |
| `event_frame_number` | int-32    | Hardware frame number that should increment by 1 when everything is working as expected. |
| `event_time_bins`    | float-32  | Due to hardware issues with retro-fitting event mode to old electronics, ISIS event mode is really a very fine histogram with between 1 and 2 microseconds bins. This field holds those time bins. |
| `event_time_offset_shift` | text | A single-element array containing the algorithm used for shuffling `event_time_offset` values across `event_time_bins`. If the value=`random` then the control program has randomised the `event_time_offset` values within the bins and downstream consumers do not need to do this. |


<!-- prettier-ignore-end -->
