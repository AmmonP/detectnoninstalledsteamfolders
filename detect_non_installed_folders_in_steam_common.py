"""
Author: Ammon Parry

Purpose: Detect any directories present in a 'steamapps/common' folder that aren't associated with an active
    install/manifest used by Steam.
"""

import logging
import re
from logging import Logger
from argparse import ArgumentParser
from os.path import isfile, isdir, basename
from os.path import join as join_path
from glob import glob

STEAM_COMMON_FOLDER = 'common'
STEAM_MANIFEST_EXTENSION = 'acf'
STEAM_FOLDER_IGNORE_LIST = {'Steam Controller Configs'.lower()}
STEAM_MANIFEST_INSTALL_DIR_KEY = '"installdir"'
MANIFEST_INSTALL_REGEX = re.compile(r'(?<=").+(?=")')


def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument('-f', '--steam-apps-directory',
                        dest='steam_apps_directory',
                        required=True,
                        help='The SteamApps folder that will be scanned to detect unlinked Steam games')

    return parser.parse_args()


def get_manifest_install_directory(manifest_file, active_logger: Logger) -> str:
    active_logger.info(f"Checking install dir of manifest: '{manifest_file}'")
    install_dir = None

    with open(manifest_file) as file:
        lines = file.readlines()

        for line in lines:
            if STEAM_MANIFEST_INSTALL_DIR_KEY in line.strip():
                found = re.findall(MANIFEST_INSTALL_REGEX,
                                   line.replace(STEAM_MANIFEST_INSTALL_DIR_KEY, ""))
                if len(found) != 1:
                    active_logger.error(f"Unable to determine directory of install dir from manifest f{manifest_file}")
                    break

                install_dir = found[0]
                break

    return install_dir


def find_all_unassociated_steam_game_directories(active_logger, steam_apps_dir):
    manifests_glob = str(join_path(steam_apps_dir, f'*.{STEAM_MANIFEST_EXTENSION}'))
    games_folder_glob = str(join_path(steam_apps_dir, f'{STEAM_COMMON_FOLDER}', '*'))

    active_logger.info(f"Using steamapps dir: '{steam_apps_dir}'")
    active_logger.info(f"Using manifests glob search: '{manifests_glob}'")
    active_logger.info(f"Using game_folder glob search: '{games_folder_glob}'")

    game_folders, manifests = get_manifests_and_detect_game_directories(games_folder_glob, manifests_glob)
    game_folders_base_paths = {basename(x): x for x in game_folders}

    active_logger.info("Detected manifests:")
    for manifest in manifests:
        active_logger.info(f"\t'{manifest}'")

    active_logger.info("Detected folders:")
    for game_folder in game_folders:
        active_logger.info(f"\t'{game_folder}'")

    installed_list = get_set_of_installed_directories(active_logger, manifests)
    return find_unmapped_directories(game_folders_base_paths, installed_list)


def get_manifests_and_detect_game_directories(games_folder_glob, manifests_glob):
    manifests = list(
        filter(lambda x: isfile(x), [file for file in glob(manifests_glob)])
    )

    game_folders = set(
        filter(
            lambda x: isdir(x) and not STEAM_FOLDER_IGNORE_LIST.__contains__(basename(x).lower()),
            [file for file in glob(games_folder_glob)]
        )
    )

    return game_folders, manifests


def get_set_of_installed_directories(active_logger, manifests):
    installed_list = set(
        map(
            lambda x: get_manifest_install_directory(x, active_logger),
            manifests
        )
    )

    for installed in installed_list:
        active_logger.info(f"Found installed directory: '{installed}'")

    return installed_list


def find_unmapped_directories(game_folders_base_paths, installed_list):
    found_uninstalled_dirs = list()

    for directory_name, detected_directory in game_folders_base_paths.items():
        if not installed_list.__contains__(directory_name):
            found_uninstalled_dirs.append(str(detected_directory))

    return sorted(found_uninstalled_dirs)


def main(active_logger: Logger):
    parsed_environment = parse_arguments()
    steam_apps_dir = parsed_environment.steam_apps_directory.strip()

    unassociated_directories = find_all_unassociated_steam_game_directories(active_logger, steam_apps_dir)

    if len(unassociated_directories) == 0:
        print("No non-associated installed directories detected")
        return

    print("Found the following directories not associated with an active install manifest:")
    for directory in unassociated_directories:
        print(f"\t'{directory}'")


if __name__ == '__main__':
    logger = logging.getLogger('SteamUnlinkedFolderFinder')
    logging.basicConfig(format='%(asctime)s: %(levelname)s: %(name)s: %(message)s')
    main(logger)
