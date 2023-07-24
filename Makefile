init:
	pdm install

pull-assets:
	git lfs pull

test-figures:
	pdm run generate_plots.py DynamicRouting1_638573_20220915_125610.hdf5

test-metrics:
	pdm run generate_metrics.py ${API_BASE} 426289 6c7ed8bc-89b0-4175-8596-0194971669b9

test-metrics-2:
	python3 generate_metrics.py http://mtrain:80 674721 65601f9e-9ebd-410a-b712-9d509756b612
