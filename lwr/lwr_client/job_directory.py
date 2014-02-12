"""
"""
import os.path
from collections import deque
import posixpath

from .util import PathHelper
from galaxy.util import verify_is_in_directory


class RemoteJobDirectory(object):
    """ Representation of a (potentially) remote LWR-style staging directory.
    """

    def __init__(self, remote_staging_directory, remote_id, remote_sep):
        self.path_helper = PathHelper(remote_sep)
        self.job_directory = self.path_helper.remote_join(
            remote_staging_directory,
            remote_id
        )

    def working_directory(self):
        return self._sub_dir('working')

    def inputs_directory(self):
        return self._sub_dir('inputs')

    def outputs_directory(self):
        return self._sub_dir('outputs')

    def configs_directory(self):
        return self._sub_dir('configs')

    def tool_files_directory(self):
        return self._sub_dir('tool_files')

    def unstructured_files_directory(self):
        return self._sub_dir('unstructured')

    @property
    def path(self):
        return self.job_directory

    @property
    def separator(self):
        return self.path_helper.separator

    def calculate_input_path(self, remote_path, input_type):
        """ Only for used by LWR client, should override for managers to
        enforce security and make the directory if needed.
        """
        directory, allow_nested_files = self._directory_for_input_type(input_type)
        return self.path_helper.remote_join(directory, remote_path)

    def _directory_for_input_type(self, input_type):
        allow_nested_files = False
        # work_dir and input_extra are types used by legacy clients...
        # Obviously this client won't be legacy because this is in the
        # client module, but this code is reused on server which may
        # serve legacy clients.
        if input_type in ['input', 'input_extra']:
            directory = self.inputs_directory()
            allow_nested_files = True
        elif input_type in ['unstructured']:
            directory = self.unstructured_files_directory()
            allow_nested_files = True
        elif input_type == 'config':
            directory = self.configs_directory()
        elif input_type == 'tool':
            directory = self.tool_files_directory()
        elif input_type in ['work_dir', 'workdir']:
            directory = self.working_directory()
        else:
            raise Exception("Unknown input_type specified %s" % input_type)
        return directory, allow_nested_files

    def _sub_dir(self, name):
        return self.path_helper.remote_join(self.job_directory, name)


def get_mapped_file(directory, remote_path, allow_nested_files=False, local_path_module=os.path, mkdir=True):
    """

    >>> import ntpath
    >>> get_mapped_file(r'C:\\lwr\\staging\\101', 'dataset_1_files/moo/cow', allow_nested_files=True, local_path_module=ntpath, mkdir=False)
    'C:\\\\lwr\\\\staging\\\\101\\\\dataset_1_files\\\\moo\\\\cow'
    >>> get_mapped_file(r'C:\\lwr\\staging\\101', 'dataset_1_files/moo/cow', allow_nested_files=False, local_path_module=ntpath)
    'C:\\\\lwr\\\\staging\\\\101\\\\cow'
    >>> get_mapped_file(r'C:\\lwr\\staging\\101', '../cow', allow_nested_files=True, local_path_module=ntpath, mkdir=False)
    Traceback (most recent call last):
    Exception: Attempt to read or write file outside an authorized directory.
    """
    if not allow_nested_files:
        name = local_path_module.basename(remote_path)
        path = local_path_module.join(directory, name)
    else:
        local_rel_path = __posix_to_local_path(remote_path, local_path_module=local_path_module)
        local_path = local_path_module.join(directory, local_rel_path)
        verify_is_in_directory(local_path, directory, local_path_module=local_path_module)
        local_directory = local_path_module.dirname(local_path)
        if mkdir and not local_path_module.exists(local_directory):
            os.makedirs(local_directory)
        path = local_path
    return path


def __posix_to_local_path(path, local_path_module=os.path):
    """
    Converts a posix path (coming from Galaxy), to a local path (be it posix or Windows).

    >>> import ntpath
    >>> __posix_to_local_path('dataset_1_files/moo/cow', local_path_module=ntpath)
    'dataset_1_files\\\\moo\\\\cow'
    >>> import posixpath
    >>> __posix_to_local_path('dataset_1_files/moo/cow', local_path_module=posixpath)
    'dataset_1_files/moo/cow'
    """
    partial_path = deque()
    while True:
        if not path or path == '/':
            break
        (path, base) = posixpath.split(path)
        partial_path.appendleft(base)
    return local_path_module.join(*partial_path)