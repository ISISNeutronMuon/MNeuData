# ISIS NeXus file

## Common fields

## Event mode

### `detector_1_events`

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
