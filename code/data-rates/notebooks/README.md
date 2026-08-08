# Notebooks

To run the notebook you will need to create a `.env` file in the parent directory with the following content:

```sh
RUN_SUMMARY_JSON_DIR=<path_to_dir_given_as_output_to_collect_run_summaries>
```

Install the requirements:

```sh
>uv pip install -r requirements.txt
```

Start Marimo:

```sh
>marimo edit notebooks/isis_data_rates.py
```

Open the browser link printed to the console.
