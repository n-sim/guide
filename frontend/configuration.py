import math
import re
import tomllib
from dataclasses import fields
from pathlib import Path

from analysis.settings import (
    ActivitySettings,
    ComparisonSettings,
    DashboardSettings,
    ParticipationSettings,
    ProcessSettings,
)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / 'config' / 'indicators.toml'


class ConfigurationError(ValueError):
    """A invalid rule configuration"""


def _keys(value, expected, location):
    if not isinstance(value, dict):
        raise ConfigurationError(f'{location} must be a TOML table')
    missing = expected - value.keys()
    unknown = value.keys() - expected
    if missing or unknown:
        details = []
        if missing:
            details.append(f'missing keys: {", ".join(sorted(missing))}')
        if unknown:
            details.append(f'unknown keys: {", ".join(sorted(unknown))}')
        raise ConfigurationError(f'{location}: {"; ".join(details)}')


def _number(value, name, minimum=0, integer=False):
    expected = (int,) if integer else (int, float)
    valid = type(value) in expected
    if valid and not integer:
        try:
            valid = math.isfinite(value)
        except OverflowError:
            valid = False
    if not valid or value < minimum:
        kind = 'integer' if integer else 'finite number'
        raise ConfigurationError(f'{name} must be a {kind} >= {minimum}')


def _validate(document):
    models = {'participation': ParticipationSettings, 'process': ProcessSettings,
              'activity': ActivitySettings, 'comparison': ComparisonSettings}
    _keys(document, set(models), 'configuration')
    for name, model in models.items():
        _keys(document[name], {field.name for field in fields(model)}, name)

    participation = document['participation']
    for key, value in participation.items():
        _number(value, f'participation.{key}')
    if participation['high_multiplier'] <= participation['low_multiplier']:
        raise ConfigurationError('participation.high_multiplier must exceed participation.low_multiplier')

    process = document['process']
    for key in ('large_commit_lines', 'short_message_chars'):
        _number(process[key], f'process.{key}', integer=True)
    words = process['generic_subject_keywords']
    if not isinstance(words, list) or any(
        not isinstance(word, str) or not re.fullmatch(r'[^\W_]+', word) or word != word.casefold()
        for word in words
    ):
        raise ConfigurationError('process.generic_subject_keywords must be an array of lowercase whole words')
    if len(words) != len(set(words)):
        raise ConfigurationError('process.generic_subject_keywords must not contain duplicates')

    activity = document['activity']
    for key in ('minimum_commits', 'minimum_periods'):
        _number(activity[key], f'activity.{key}', minimum=2, integer=True)
    _number(activity['window_days'], 'activity.window_days', minimum=1, integer=True)
    for key in ('low_daily_commits', 'low_run_alert_days'):
        _number(activity[key], f'activity.{key}', integer=True)
    for key in ('variability_info_cv', 'variability_warning_cv'):
        _number(activity[key], f'activity.{key}')
    if activity['variability_warning_cv'] <= activity['variability_info_cv']:
        raise ConfigurationError('activity.variability_warning_cv must exceed activity.variability_info_cv')

    tolerance = document['comparison']['tolerance']
    _number(tolerance, 'comparison.tolerance')
    if tolerance > 1:
        raise ConfigurationError('comparison.tolerance must be <= 1 (a proportion, not a percentage)')

    return DashboardSettings(
        participation=ParticipationSettings(**participation),
        process=ProcessSettings(**{**process, 'generic_subject_keywords': tuple(words)}),
        activity=ActivitySettings(**activity),
        comparison=ComparisonSettings(**document['comparison']),
    )


def load_configuration(path: str | Path = DEFAULT_CONFIG_PATH) -> DashboardSettings:
    path = Path(path)
    try:
        with path.open('rb') as file:
            document = tomllib.load(file)
        return _validate(document)
    except (OSError, tomllib.TOMLDecodeError, ConfigurationError) as error:
        raise ConfigurationError(f'Invalid indicator configuration ({path}): {error}') from error
