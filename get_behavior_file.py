import pathlib
import np_session


def get_behavior_session_storage_dir(foraging_id_and_filename) -> pathlib.Path:
    """ * `storage_directory` isn't being populated in LIMS if upload job fails * will need to manually construct path >>> d = get_behavior_session_storage_dir(('3b70feba-8572-4cd8-884b-35ff62975d39', 'DynamicRouting1_366122_20230414_120213.hdf5')) >>> d.as_posix() '//allen/programs/braintv/production/neuralcoding/prod0/specimen_657428270/behavior_session_1264106353' """
    foraging_id, filename = foraging_id_and_filename
    _, mouse_id, *_ = filename.split('_')
    mouse = np_session.Mouse(mouse_id)
    if not mouse.lims:
        raise ValueError(f'Could not find mouse {mouse_id} in LIMS')

    if not mouse.lims.get('behavior_sessions'):
        raise ValueError(
            f'Could not find behavior sessions for mouse {mouse_id} in LIMS')

    behavior_sessions = tuple(session for session in mouse.lims['behavior_sessions'] if session['foraging_id'].replace(
        '-', '') == foraging_id.replace('-', ''))

    if not behavior_sessions:
        raise ValueError(
            f'Could not find behavior session for foraging_id {foraging_id} in LIMS')
    raise Exception(mouse.lims.path)
    return np_config.normalize_path(mouse.lims.path / f'behavior_session_{behavior_sessions[0]["id"]}')


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("foraging_id_and_filename", type=str)

    args = parser.parse_args()

    path = get_behavior_session_storage_dir(args.foraging_id_and_filename)
    print(path)
