import logging
import pathlib
import platform
import shutil
import subprocess
import sys
from tempfile import NamedTemporaryFile
from typing import List, Union

from tufup.utils import remove_path

logger = logging.getLogger(__name__)

CURRENT_PLATFORM = platform.system()
ON_WINDOWS = CURRENT_PLATFORM == 'Windows'
ON_MAC = CURRENT_PLATFORM == 'Darwin'
PLATFORM_SUPPORTED = ON_WINDOWS or ON_MAC


def install_update(
        src_dir: Union[pathlib.Path, str],
        dst_dir: Union[pathlib.Path, str],
        purge_dst_dir: bool = False,
        exclude_from_purge: List[Union[pathlib.Path, str]] = None,
        **kwargs,
):
    """
    Installs update files using platform specific installation script. The
    actual installation script copies the files and folders from `src_dir` to
    `dst_dir`.

    If `purge_dst_dir` is `True`, *ALL* files and folders are deleted from
    `dst_dir` before copying.

    **DANGER**:

    ONLY use `purge_dst_dir=True` if your app is properly installed in its
    own *separate* directory, such as %PROGRAMFILES%\MyApp.

    DO NOT use `purge_dst_dir=True` if your app executable is running
    directly from a folder that also contains unrelated files or folders,
    such as the Desktop folder or the Downloads folder, because this
    unrelated content would be then also be deleted.

    Individual files and folders can be excluded from purge using e.g.

        exclude_from_purge=['path\\to\\file1', r'"path to\file2"', ...]

    If `purge_dst_dir` is `False`, the `exclude_from_purge` argument is
    ignored.
    """
    if ON_WINDOWS:
        _install_update = _install_update_win
    elif ON_MAC:
        _install_update = _install_update_mac
    else:
        raise RuntimeError('This platform is not supported.')
    return _install_update(
        src_dir=src_dir,
        dst_dir=dst_dir,
        purge_dst_dir=purge_dst_dir,
        exclude_from_purge=exclude_from_purge,
        **kwargs,
    )


WIN_LOG_LINES = """
call :log > "{log_file_path}" 2>&1
:log
"""
WIN_ROBOCOPY_OVERWRITE = (
    '/e',  # include subdirectories, even if empty
    '/move',  # deletes files and dirs from source dir after they've been copied
    '/v',  # verbose (show what is going on)
)
WIN_ROBOCOPY_PURGE = '/purge'  # delete all files and dirs in destination folder
WIN_ROBOCOPY_EXCLUDE_FROM_PURGE = '/xf'  # exclude specified paths from purge

# https://stackoverflow.com/a/20333575
WIN_MOVE_FILES_BAT = """@echo off
{log_lines}
echo Moving app files...
rem wait a few seconds for caller to relinquish locks etc. 
timeout /t 2
robocopy "{src}" "{dst}" {options}
echo Done.
rem Delete self
(goto) 2>nul & del "%~f0"
"""


def run_bat_as_admin(file_path: Union[pathlib.Path, str]):
    """
    Request elevation for windows command interpreter (opens UAC prompt) and
    then run the specified .bat file.

    Returns True if successfully started, does not block, can continue after
    calling process exits.
    """
    from ctypes import windll
    # https://docs.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecutew
    result = windll.shell32.ShellExecuteW(
        None,  # handle to parent window
        'runas',  # verb
        'cmd.exe',  # file on which verb acts
        ' '.join(['/c', str(file_path)]),  # parameters
        None,  # working directory (default is cwd)
        1,  # show window normally
    )
    return result > 32


def _install_update_win(
        src_dir: Union[pathlib.Path, str],
        dst_dir: Union[pathlib.Path, str],
        purge_dst_dir: bool,
        exclude_from_purge: List[Union[pathlib.Path, str]],
        as_admin: bool = False,
        log_file_name: str = None,
        robocopy_options_override: List[str] = None,
):
    """
    Create a batch script that moves files from src to dst, then run the
    script in a new console, and exit the current process.

    The script is created in a default temporary directory, and deletes
    itself when done.

    The `as_admin` options allows installation as admin (opens UAC dialog).

    The `debug` option will log the output of the install script to a file in
    the dst_dir.

    Options for [robocopy][1] can be overridden completely by passing a list
    of option strings to `robocopy_options_override`. This will cause the
    purge arguments to be ignored as well.

    [1]: https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy
    """
    if robocopy_options_override is None:
        options = list(WIN_ROBOCOPY_OVERWRITE)
        if purge_dst_dir:
            options.append(WIN_ROBOCOPY_PURGE)
            if exclude_from_purge:
                options.append(WIN_ROBOCOPY_EXCLUDE_FROM_PURGE)
                options.extend(exclude_from_purge)
    else:
        # empty list [] simply clears all options
        options = robocopy_options_override
    options_str = ' '.join(options)
    log_lines = ''
    if log_file_name:
        log_file_path = pathlib.Path(dst_dir) / log_file_name
        log_lines = WIN_LOG_LINES.format(log_file_path=log_file_path)
        logger.info(f'logging install script output to {log_file_path}')
    script_content = WIN_MOVE_FILES_BAT.format(
        src=src_dir, dst=dst_dir, options=options_str, log_lines=log_lines
    )
    logger.debug(f'writing windows batch script:\n{script_content}')
    with NamedTemporaryFile(
            mode='w', prefix='tufup', suffix='.bat', delete=False
    ) as temp_file:
        temp_file.write(script_content)
    logger.debug(f'temporary batch script created: {temp_file.name}')
    script_path = pathlib.Path(temp_file.name).resolve()
    logger.debug(f'starting script in new console: {script_path}')
    # start the script in a separate process, non-blocking
    if as_admin:
        run_bat_as_admin(file_path=script_path)
    else:
        # we use Popen() instead of run(), because the latter blocks execution
        subprocess.Popen(
            [script_path], creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    logger.debug('exiting')
    sys.exit(0)


def _install_update_mac(
        src_dir: Union[pathlib.Path, str],
        dst_dir: Union[pathlib.Path, str],
        purge_dst_dir: bool,
        exclude_from_purge: List[Union[pathlib.Path, str]],
        **kwargs,
):
    # todo: implement as_admin and debug kwargs for mac
    logger.debug(f'Kwargs not used: {kwargs}')
    if purge_dst_dir:
        exclude_from_purge = [  # enforce path objects
            pathlib.Path(item) for item in exclude_from_purge
        ] if exclude_from_purge else []
        logger.debug(f'Purging content of {dst_dir}')
        for path in pathlib.Path(dst_dir).iterdir():
            if path not in exclude_from_purge:
                remove_path(path=path)
    logger.debug(f'Moving content of {src_dir} to {dst_dir}.')
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    # Note: the src_dir is typically a temporary directory, but we'll clear
    # it anyway just to be consistent with the windows implementation
    for path in pathlib.Path(src_dir).iterdir():
        remove_path(path=path)
    logger.debug(f'Restarting application, running {sys.executable}.')
    subprocess.Popen(sys.executable, shell=True)  # nosec
    sys.exit(0)
