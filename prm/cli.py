# MIT License

# Copyright (c) 2020 Nihaal Sangha

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import os
import subprocess
import textwrap
from pathlib import Path
import json
import click

import pecho
from prm import __version__

from .config import Config, ConfigKey


def echo(text: str, newline: bool = True) -> None:
    pecho.echo(text, newline=newline, print_func=click.echo)


def process_multiline(text: str) -> str:
    return textwrap.dedent(text).strip()


def execute(command: str) -> None:
    subprocess.run(command, shell=True)


config = Config()


@click.group()
@click.version_option(__version__, prog_name='plex-rclone-manager')
def cli():
    pass


@cli.command()
@click.option('--after-manual-import', is_flag=True)
@click.option('--manual-import-partials', is_flag=True)
def clean(after_manual_import: bool, manual_import_partials: bool):
    config.clear_overriden()

    cmd = ''
    if after_manual_import:
        cmd += process_multiline(
            f"""
            path="{config.get(ConfigKey.DOWNLOAD_COMPLETE_PATH)}"
            echo "Deleting extra files"
            find ${{path}} -type f \\( -iname "*sample*" -o -iname "*.nfo" -o -iname "*.nzb" -o -iname "*.jpg" \
            -o -iname "*.srr" -o -iname "*.url" -o -iname "*.txt" \\) -print -delete
            echo "Deleting empty Films folders"
            find ${{path}}/Films -type d -empty -print -delete
            echo "Deleting empty TV folders"
            find ${{path}}/TV -type d -empty -print -delete
            echo "Deleting empty Music folders"
            find ${{path}}/Music -type d -empty -print -delete
            """
        )
    if manual_import_partials:
        cmd += process_multiline(
            f"""
            find {config.get(ConfigKey.LOCAL_FILES_PATH)} -type f -iname "*.partial~" -not \\
                -path {config.get(ConfigKey.LOCAL_FILES_PATH)}/download/* -print -delete
            find {config.get(ConfigKey.LOCAL_FILES_PATH)} -mindepth 1 -type d -not \\
                -path {config.get(ConfigKey.LOCAL_FILES_PATH)}/download/* -empty -print -delete
            """
        )


@cli.command()
@click.option('--all', is_flag=True)
@click.option('--local-server-setup', is_flag=True)
@click.option('--media', is_flag=True)
@click.option('--plex-data', is_flag=True)
@click.option('--rclone-remote', '-r', default='', type=str)
@click.option('--plex-media-server-path', '-p', default='', type=str)
def upload(
    all: bool, local_server_setup: bool, media: bool, plex_data: bool, rclone_remote: str, plex_media_server_path: str
):
    config.clear_overriden()

    if all and any((local_server_setup, media, plex_data)):
        echo("If --all is specified, no other related options should be")
        raise click.Abort()
    if all:
        local_server_setup = media = plex_data = True
    elif not any((local_server_setup, media, plex_data)):
        echo("No target options given")
        raise click.Abort()

    if rclone_remote:
        config.set_value(ConfigKey.RCLONE_REMOTE, rclone_remote)
    if plex_media_server_path:
        config.set_value(ConfigKey.PLEX_MEDIA_SERVER_PATH, plex_media_server_path)

    cmd = ''
    if local_server_setup:
        cmd += process_multiline(
            f"""
            /usr/local/bin/rclone sync -v --progress \\
            ~/scripts \\
            {config.get(ConfigKey.RCLONE_REMOTE)}:/Backups/Server/Scripts

            /usr/local/bin/rclone sync -v --progress \\
            ~/.startup \\
            {config.get(ConfigKey.RCLONE_REMOTE)}:/Backups/Server/Startup

            /usr/local/bin/rclone sync -v --progress \\
            ~/.shutdown \\
            {config.get(ConfigKey.RCLONE_REMOTE)}:/Backups/Server/Shutdown

            file_path=~/"tmp/plex_server_backups/dot_config/$(date +"%Y/%m")"
            mkdir -p "${{file_path}}"
            /bin/tar -czhf "${{file_path}}/$(date +"%Y-%m-%d").tar.gz" \\
            -C ~ \\
            .config

            /usr/local/bin/rclone move \\
            ~/tmp/plex_server_backups/dot_config {config.get(ConfigKey.RCLONE_REMOTE)}:/Backups/Server/Config \\
            -v \\
            --progress
            """
        )
    if media:
        cmd += process_multiline(
            f"""
            echo "Moving processed content"
            /usr/local/bin/rclone move \\
            "{config.get(ConfigKey.LOCAL_FILES_PATH)}" {config.get(ConfigKey.RCLONE_REMOTE)}: \\
            -v \\
            --progress \\
            --delete-empty-src-dirs \\
            --exclude "/download/**" \\
            --exclude "*.partial~" \\
            --transfers=1 \\
            --drive-stop-on-upload-limit
            """
        )
    if plex_data:
        cmd += process_multiline(
            f"""
            file_path=~/"tmp/plex_server_backups/plex_data/$(date +"%Y/%m")"
            mkdir -p "${{file_path}}"
            /bin/tar -czhf  "${{file_path}}/$(date +"%Y-%m-%d").tar.gz" \\
            -C ~ \\
            "{config.get(ConfigKey.PLEX_MEDIA_SERVER_PATH)}Media/" \\
            "{config.get(ConfigKey.PLEX_MEDIA_SERVER_PATH)}Metadata/" \\
            "{config.get(ConfigKey.PLEX_MEDIA_SERVER_PATH)}Plug-ins/" \\
            "{config.get(ConfigKey.PLEX_MEDIA_SERVER_PATH)}Plug-in Support/"

            /usr/local/bin/rclone move \\
            ~/tmp/plex_server_backups/plex_data {config.get(ConfigKey.RCLONE_REMOTE)}:/Backups/Plex \\
            -v \\
            --progress
            """
        )

    execute(cmd)


@cli.group()
def plex():
    pass


@plex.command(name='preview-thumbnails')
@click.option('--summary', '-s', is_flag=True)
@click.option('--print', '-p', 'print_folders', is_flag=True)
@click.option('--json', '-j', 'print_json', is_flag=True)
@click.option('--progress', '-p', is_flag=True)
@click.option('--plex-media-server-path', '-pp', default='', type=str)
def preview_thumbnails(
    summary: bool, print_folders: bool, print_json: bool, progress: bool, plex_media_server_path: str
):
    config.clear_overriden()

    if not any((summary, print_folders)):
        echo("Summary or print must be given")
        raise click.Abort()

    if print_json is True and summary is False:
        echo("Summary must be given when using JSON")
        raise click.Abort()

    if progress is True and print_json is True:
        echo("Progress does not support JSON")
        raise click.Abort()

    if progress is True and summary is False:
        echo("Summary must be given if using progress")
        raise click.Abort()

    # if progress is True and print_folders is True:
    #     echo("Progress does not support printing folders")
    #     raise click.Abort()

    if plex_media_server_path:
        config.set_value(ConfigKey.PLEX_MEDIA_SERVER_PATH, plex_media_server_path)

    missing = 0
    total = 0

    path = Path(config.get(ConfigKey.PLEX_MEDIA_SERVER_PATH) + 'Media/localhost')
    if not path.exists():
        echo("Plex Media Server/Media/localhost not found")
        raise click.Abort()

    for a in os.scandir(path):
        if not a.is_dir():
            continue
        for b in os.scandir(a.path):
            if not a.is_dir() or not b.path.endswith('.bundle'):
                continue
            total += 1
            if not Path(b.path).joinpath('Contents', 'Indexes', 'index-sd.bif').exists():
                missing += 1
                if print_folders is True:
                    echo(b.path[len('localhost/') :], newline=True)
                if progress is True:
                    echo(
                        f'Remaining: {missing}\nProcessed: {total-missing}\nTotal: {total}\nRemaining: {round(missing*100/total, 2)}%',
                        False,
                    )

    if summary is True:
        if print_json is True:
            echo(json.dumps({'remaining': missing, 'total': total}))
        else:
            echo(
                f'Remaining: {missing}\nProcessed: {total-missing}\nTotal: {total}\nRemaining: {round(missing*100/total, 2)}%'
            )