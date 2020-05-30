import enum
from pathlib import Path
from typing import Any, List, Optional

import click
import toml
import yaml


class ConfigKey(enum.Enum):
    RCLONE_REMOTE = enum.auto()
    LOCAL_FILES_PATH = enum.auto()
    MOUNT_RCLONE_PATH = enum.auto()
    MOUNT_MERGE_PATH = enum.auto()
    DOWNLOAD_COMPLETE_PATH = enum.auto()
    # DOWNLOAD_PATH = enum.auto()
    PLEX_MEDIA_SERVER_PATH = enum.auto()


class Overriden(enum.Enum):
    ONLY_OVERRIDEN = enum.auto()
    ONLY_CONFIG = enum.auto()
    OVERRIDEN_THEN_CONFIG = enum.auto()


class Config:
    def __init__(self) -> None:
        self._loaded: bool = False
        self._cached_config = {}
        self._overriden = {}

        self._path_config_values: List[ConfigKey] = [
            ConfigKey.LOCAL_FILES_PATH,
            ConfigKey.MOUNT_RCLONE_PATH,
            ConfigKey.MOUNT_MERGE_PATH,
            ConfigKey.DOWNLOAD_COMPLETE_PATH,
            # ConfigKey.DOWNLOAD_PATH,
            ConfigKey.PLEX_MEDIA_SERVER_PATH,
        ]

    def _clean(self, overriden: bool = False) -> None:
        for config_key in self._path_config_values:
            if overriden is True:
                config_value = self._get(config_key, overriden=Overriden.ONLY_OVERRIDEN)
            else:
                config_value = self._get(config_key, overriden=Overriden.ONLY_CONFIG)
            if config_value:
                if config_value.endswith('/'):
                    raise ValueError("All paths should have a leading slash")
                self._set(config_key, str(Path(config_value).expanduser()), overriden=overriden)

    def _load(self) -> None:
        for file_path in (
            '~/.config/prm.json',
            '~/.config/prm.yml',
            '~/.config/prm.yaml',
            '~/.config/prm.toml',
        ):
            path = Path(file_path).expanduser()
            if not path.exists():
                continue
            with open(path) as fp:
                if str(path).endswith(('.json', '.yml', '.yaml')):
                    config = yaml.load(fp)
                elif str(path).endswith('.toml'):
                    config = toml.load(fp)
                else:
                    raise ValueError("Unsupported file extension")
                self._cached_config = dict(config)
                break

        self._loaded = True

        self._clean()

    def _load_if_needed(self) -> None:
        if self._loaded is False:
            self._load()

    def _set(self, config_key: ConfigKey, value: Any, *, overriden: bool = False) -> None:
        if overriden is True:
            self._overriden[config_key.name.lower()] = value
        else:
            self._cached_config[config_key.name.lower()] = value

    def set_value(self, config_key: ConfigKey, value: Any) -> None:
        self._set(config_key, value, overriden=True)
        self._clean()

    def _get(self, config_key: ConfigKey, required: bool = False, *, overriden: Overriden) -> Optional[Any]:
        key = config_key.name.lower()
        if key in self._overriden and (
            overriden is Overriden.ONLY_OVERRIDEN or overriden is Overriden.OVERRIDEN_THEN_CONFIG
        ):
            return self._overriden[key]
        if overriden is Overriden.ONLY_OVERRIDEN:
            if required is True:
                raise ValueError("Value not given for required key")
            return
        self._load_if_needed()

        value = self._cached_config.get(key)
        if required is True and not value:
            raise ValueError("Value not given for required key")
        return value

    def get(self, config_key: ConfigKey, required: bool = True) -> Optional[Any]:
        return self._get(config_key, required, overriden=Overriden.OVERRIDEN_THEN_CONFIG)

    def clear_overriden(self):
        self._overriden = {}
