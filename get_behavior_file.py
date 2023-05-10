import re
import pathlib
import np_session
import np_config


def get_behavior_session_storage_dir(subject_id: str, foraging_id: str) -> pathlib.Path:
    """ * `storage_directory` isn't being populated in LIMS if upload job fails * will need to manually construct path >>> d = get_behavior_session_storage_dir(('3b70feba-8572-4cd8-884b-35ff62975d39', 'DynamicRouting1_366122_20230414_120213.hdf5')) >>> d.as_posix() '//allen/programs/braintv/production/neuralcoding/prod0/specimen_657428270/behavior_session_1264106353' """
    mouse = np_session.Mouse(subject_id)
    if not mouse.lims:
        raise ValueError(f'Could not find mouse {subject_id} in LIMS')

    if not mouse.lims.get('behavior_sessions'):
        raise ValueError(
            f'Could not find behavior sessions for mouse {subject_id} in LIMS')

    behavior_sessions = tuple(
        session for session in mouse.lims['behavior_sessions']
        if session['foraging_id'].replace('-', '') == foraging_id.replace('-', '')
    )

    if not behavior_sessions:
        raise ValueError(
            f'Could not find behavior session for foraging_id {foraging_id} in LIMS')

    hdf5s = list(np_config.normalize_path(mouse.lims.path /
                 f'behavior_session_{behavior_sessions[0]["id"]}').glob("*.hdf5"))

    behavior_filename_pattern = f"DynamicRouting1_{subject_id}" + \
        "_\d{8}_\d+?\.hdf5"
    behavior_files = [
        path for path in hdf5s
        if re.match(behavior_filename_pattern, path.name) is not None
    ]

    if len(behavior_files) < 1:
        raise Exception(
            "No behavior files found from search pattern. pattern=%s" % behavior_filename_pattern)

    if len(behavior_files) > 2:
        raise Exception(
            "More than one hdf5 file detected. Only one should be present. This is a critical error.")

    return behavior_files[0]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("subject_id", type=str)
    parser.add_argument("foraging_id", type=str)

    args = parser.parse_args()

    path = get_behavior_session_storage_dir(args.subject_id, args.foraging_id)

    print(path)
