init:
	pdm install

pull-assets:
	git lfs pull

test-figures:
	pdm run generate_plots.py DynamicRouting1_638573_20220915_125610.hdf5

test-metrics:
	pdm run generate_metrics.py ${API_BASE} 426289 6c7ed8bc-89b0-4175-8596-0194971669b9
