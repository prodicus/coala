import os
import sys
import unittest

from coalib.bearlib.abstractions.Linter import Linter
from coalib.results.Result import Result
from coalib.results.RESULT_SEVERITY import RESULT_SEVERITY
from coalib.settings.Section import Section


def get_testfile_name(name):
    """
    Gets the full path to a testfile inside ``linter_test_files`` directory.

    :param name: The filename of the testfile to get the full path for.
    :return:     The full path to given testfile name.
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        "linter_test_files",
                         name)


class LinterComponentTest(unittest.TestCase):

    class EmptyTestLinter:
        pass

    def setUp(self):
        self.section = Section("TEST_SECTION")

    def test_decorator_creation(self):
        with self.assertRaises(ValueError):
            Linter("some-executable", invalid_arg=88)

        with self.assertRaises(ValueError):
            Linter("some-executable", diff_severity=RESULT_SEVERITY.MAJOR)

        with self.assertRaises(ValueError):
            Linter("some-executable", diff_message="Custom message")

        with self.assertRaises(ValueError):
            Linter("some-executable",
                   provides_correction=True,
                   output_regex=".*")

        with self.assertRaises(ValueError):
            Linter("some-executable",
                   provides_correction=True,
                   severity_map={})

    def test_get_executable(self):
        uut = Linter("some-executable", output_regex="")(self.EmptyTestLinter)
        self.assertEqual(uut.get_executable(), "some-executable")

    def test_check_prerequisites(self):
        uut = Linter(sys.executable, output_regex="")(self.EmptyTestLinter)
        self.assertTrue(uut.check_prerequisites())

        uut = (Linter("invalid_nonexisting_programv412", output_regex="")
               (self.EmptyTestLinter))
        self.assertEqual(uut.check_prerequisites(),
                         "'invalid_nonexisting_programv412' is not installed.")

    def test_execute_command(self):
        test_program_path = get_testfile_name("stdout_stderr.py")
        uut = Linter(sys.executable, output_regex="")(self.EmptyTestLinter)

        # The test program puts out the stdin content (only the first line) to
        # stdout and the arguments passed to stderr.
        stdout, stderr = uut._execute_command(
            [test_program_path, "some_argument"],
            stdin="display content")

        self.assertEqual(stdout, "display content\n")
        self.assertEqual(stderr, "['some_argument']\n")

    def test_process_output_corrected(self):
        # TODO Ahhh I need to instantiate the bear...
        uut = (Linter("", provides_correction=True)
               (self.EmptyTestLinter)
               (self.section, None))

    def test_process_output_issues(self):
        test_output = ("12:4-14:0-Serious issue (error) -> ORIGIN=X\n"
                       "0:0-0:1-This is a warning (warning) -> ORIGIN=Y\n"
                       "813:77-1024:32-Just a note (info) -> ORIGIN=Z\n")
        regex = (r"(?P<line>\d+):(?P<column>\d+)-"
                 r"(?P<end_line>\d+):(?P<end_column>\d+)-"
                 r"(?P<message>.*) \((?P<severity>.*)\) -> "
                 r"ORIGIN=(?P<origin>.*)")

        uut = (Linter("", output_regex=regex)
               (self.EmptyTestLinter)
               (self.section, None))
        sample_file = "some-file.xtx"
        results = list(uut._process_output(test_output, sample_file, [""]))
        expected = [Result.from_values("X",
                                       "Serious issue",
                                       sample_file,
                                       12,
                                       4,
                                       14,
                                       0,
                                       RESULT_SEVERITY.MAJOR),
                    Result.from_values("Y",
                                       "This is a warning",
                                       sample_file,
                                       0,
                                       0,
                                       0,
                                       1,
                                       RESULT_SEVERITY.NORMAL),
                    Result.from_values("Z",
                                       "Just a note",
                                       sample_file,
                                       813,
                                       77,
                                       1024,
                                       32,
                                       RESULT_SEVERITY.MINOR)]

        self.assertEqual(results, expected)

    def test_section_settings_forwarding(self):
        pass
        # TODO Use bear.execute() and pass in section values `create_arguments`
        # TODO is able to take.

    def test_grab_output(self):
        uut = (Linter("", use_stderr=False, output_regex="")
               (self.EmptyTestLinter))
        self.assertEqual(uut._grab_output("std", "err"), "std")

        uut = (Linter("", use_stderr=True, output_regex="")
               (self.EmptyTestLinter))
        self.assertEqual(uut._grab_output("std", "err"), "err")

    def test_pass_file_as_stdin_if_needed(self):
        uut = (Linter("", use_stdin=False, output_regex="")
               (self.EmptyTestLinter))
        self.assertIsNone(uut._pass_file_as_stdin_if_needed(["contents"]))

        uut = Linter("", use_stdin=True, output_regex="")(self.EmptyTestLinter)
        self.assertEqual(uut._pass_file_as_stdin_if_needed(["contents"]),
                         ["contents"])

    def test_generate_config(self):
        uut = Linter("", output_regex="")(self.EmptyTestLinter)
        with uut._create_config("filename", []) as config_file:
            self.assertIsNone(config_file)

        class ConfigurationTestLinter:
            @staticmethod
            def generate_config(filename, file, val):
                return "config_value = " + str(val)

        uut = Linter("", output_regex="")(ConfigurationTestLinter)
        with uut._create_config("filename", [], val=88) as config_file:
            self.assertTrue(os.path.isfile(config_file))
            with open(config_file, mode="r") as fl:
                self.assertEqual(fl.read(), "config_value = 88")
        self.assertFalse(os.path.isfile(config_file))


class LinterReallifeTest(unittest.TestCase):

    def setUp(self):
        self.section = Section("REALLIFE_TEST_SECTION")

        self.test_program_path = get_testfile_name("test_linter.py")
        self.test_program_regex = (
            r"L(?P<line>\d+)C(?P<column>\d+)-"
            r"L(?P<end_line>\d+)C(?P<end_column>\d+):"
            r" (?P<message>.*) \| (?P<severity>.+) SEVERITY")
        self.test_program_severity_map = {"MAJOR": RESULT_SEVERITY.MAJOR}

        self.testfile_path = get_testfile_name("test_file.txt")
        with open(self.testfile_path, mode="r") as fl:
            self.testfile_content = fl.read()

        self.testfile2_path = get_testfile_name("test_file2.txt")
        with open(self.testfile2_path, mode="r") as fl:
            self.testfile2_content = fl.read()

    def test_nostdin_nostderr_noconfig_nocorrection(self):
        class Handler:
            @staticmethod
            def create_arguments(filename, file, config_file):
                self.assertEqual(filename, self.testfile_path)
                self.assertEqual(file, self.testfile_content)
                self.assertIsNone(config_file)
                return self.test_program_path, filename

        uut = (Linter(sys.executable,
                      output_regex=self.test_program_regex,
                      severity_map=self.test_program_severity_map)
               (Handler)
               (self.section, None))

        results = list(uut.run(self.testfile_path, self.testfile_content))
        expected = [Result.from_values(uut,
                                       "Invalid char ('0')",
                                       self.testfile_path,
                                       3,
                                       0,
                                       3,
                                       1,
                                       RESULT_SEVERITY.MAJOR),
                    Result.from_values(uut,
                                       "Invalid char ('.')",
                                       self.testfile_path,
                                       5,
                                       0,
                                       5,
                                       1,
                                       RESULT_SEVERITY.MAJOR),
                    Result.from_values(uut,
                                       "Invalid char ('p')",
                                       self.testfile_path,
                                       9,
                                       0,
                                       9,
                                       1,
                                       RESULT_SEVERITY.MAJOR)]

        self.assertEqual(results, expected)

    def test_stdin_stderr_noconfig_nocorrection(self):
        class Handler:
            @staticmethod
            def create_arguments(filename, file, config_file):
                self.assertEqual(filename, self.testfile2_path)
                self.assertEqual(file, self.testfile2_content)
                self.assertIsNone(config_file)
                return (self.test_program_path,
                        "--use_stderr",
                        "--use_stdin",
                        filename)

        uut = (Linter(sys.executable,
                      use_stdin=True,
                      use_stderr=True,
                      output_regex=self.test_program_regex,
                      severity_map=self.test_program_severity_map)
               (Handler)
               (self.section, None))

        results = list(uut.run(self.testfile2_path, self.testfile2_content))
        expected = [Result.from_values(uut,
                                       "Invalid char ('X')",
                                       self.testfile2_path,
                                       0,
                                       0,
                                       0,
                                       1,
                                       RESULT_SEVERITY.MAJOR),
                    Result.from_values(uut,
                                       "Invalid char ('i')",
                                       self.testfile2_path,
                                       4,
                                       0,
                                       4,
                                       1,
                                       RESULT_SEVERITY.MAJOR)]

        self.assertEqual(results, expected)

    def test_nostdin_nostderr_noconfig_correction(self):
        class Handler:
            @staticmethod
            def create_arguments(filename, file, config_file):
                self.assertEqual(filename, self.testfile_path)
                self.assertEqual(file, self.testfile_content)
                self.assertIsNone(config_file)
                return self.test_program_path, "--correct", filename

        uut = (Linter(sys.executable, provides_correction=True)
               (Handler)
               (self.section, None))

        results = list(uut.run(self.testfile_path, self.testfile_content))
        # TODO Adjust results for diff support^^
        expected = [Result.from_values(uut,
                                       "Inconsistency found",
                                       self.testfile_path,
                                       3,
                                       0,
                                       3,
                                       1,
                                       RESULT_SEVERITY.MAJOR),
                    Result.from_values(uut,
                                       "Inconsistency found",
                                       self.testfile_path,
                                       5,
                                       0,
                                       5,
                                       1,
                                       RESULT_SEVERITY.MAJOR),
                    Result.from_values(uut,
                                       "Inconsistency found",
                                       self.testfile_path,
                                       9,
                                       0,
                                       9,
                                       1,
                                       RESULT_SEVERITY.MAJOR)]

        self.assertEqual(results, expected)

        # TODO Test non-defaults
        uut = (Linter(sys.executable,
                      provides_correction=True,
                      diff_severity=RESULT_SEVERITY.MINOR,
                      diff_message="Custom message")
               (Handler)
               (self.section, None))

    def test_stdin_stderr_config_nocorrection(self):
        class Handler:
            @staticmethod
            def generate_config(filename, file, some_val):
                self.assertEqual(filename, self.testfile_path)
                self.assertEqual(file, self.testfile_content)
                # some_val shall only test the argument delegation from run().
                self.assertEqual(some_val, 33)

                return "\n".join(["use_stdin", "use_stderr"])

            @staticmethod
            def create_arguments(filename, file, config_file, some_val):
                self.assertEqual(filename, self.testfile_path)
                self.assertEqual(file, self.testfile_content)
                self.assertIsNotNone(config_file)
                self.assertEqual(some_val, 33)

                return self.test_program_path, "--config", config_file

        uut = (Linter(sys.executable,
                      use_stdin=True,
                      use_stderr=True,
                      output_regex=self.test_program_regex)
               (Handler)
               (self.section, None))

        results = list(uut.run(self.testfile_path, self.testfile_content))
        expected = [Result.from_values(uut,
                                       "Invalid char ('0')",
                                       self.testfile_path,
                                       3,
                                       0,
                                       3,
                                       1,
                                       RESULT_SEVERITY.MAJOR),
                    Result.from_values(uut,
                                       "Invalid char ('.')",
                                       self.testfile_path,
                                       5,
                                       0,
                                       5,
                                       1,
                                       RESULT_SEVERITY.MAJOR),
                    Result.from_values(uut,
                                       "Invalid char ('p')",
                                       self.testfile_path,
                                       9,
                                       0,
                                       9,
                                       1,
                                       RESULT_SEVERITY.MAJOR)]

        self.assertEqual(results, expected)

    def test_stdin_stderr_config_correction(self):
        # TODO
        pass