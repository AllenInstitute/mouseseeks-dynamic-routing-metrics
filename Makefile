init:
	pdm install

pull-assets:
	git lfs pull

test-figures:
	pdm run generate_plots.py DynamicRouting1_638573_20220915_125610.hdf5

test-metrics:
	pdm run generate_metrics.py ${API_BASE} 426289 3110b2b6-20ec-4ed3-83b4-c6a929f19975
