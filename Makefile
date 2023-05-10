init:
	pdm install

pull-assets:
	git lfs pull

test-figures:
	pdm run generate_plots.py DynamicRouting1_638573_20220915_125610.hdf5

test-metrics:
	pdm run generate_metrics.py ${API_BASE} 175383 7c3858f7-9c92-4215-8f0e-d3077f00223c
