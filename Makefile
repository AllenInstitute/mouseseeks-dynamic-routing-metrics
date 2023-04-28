init:
	pdm install

pull-assets:
	git lfs pull

test-figures:
	pdm run generate_plots.py DynamicRouting1_638573_20220915_125610.hdf5
