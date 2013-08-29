# Copyright (c) 2013, Red Hat, Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of the FreeBSD Project.
#
# Authors: Michal Minar <miminar@redhat.com>
#
"""
Sub package with formatter classes used to render and output results.

Each formatter has an ``produce_output()`` method taking one argument which
gets rendered and printed to output stream. Each formatter expects different
argument, please refer to doc string of particular class.
"""

import itertools

class Formatter(object):
    """
    Base formatter class.

    It produces string representation of given argument and prints it.

    This formatter supports following commands:
        NewHostCommand.

    :param stream: (``file``) Output stream.
    :param padding: (``int``) Number of leading spaces to print at each line.
    """

    def __init__(self, stream, padding=0):
        if not isinstance(padding, (int, long)):
            raise TypeError("padding must be an integer")
        if padding < 0:
            padding = 0
        self.out = stream
        self.padding = padding

    def render_value(self, val):
        """
        Rendering function for single value.

        :param val: Any value to render.
        :rtype: (``str``) Value converted to its string representation.
        """
        if isinstance(val, unicode):
            return val.encode('utf-8')
        if not isinstance(val, str):
            val = str(val)
        return val

    def print_line(self, line, *args, **kwargs):
        """
        Prints single line. Output message is prefixed with ``padding`` spaces,
        formated and printed to output stream.

        :param line: (``str``) Message to print, it can contain markers for
            other arguments to include according to ``format_spec`` language.
            Please refer to ``Format Specification Mini-Language`` in python
            documentation.
        :param args: (``list``) Positional arguemnts to ``format`` function of
            ``line`` argument.
        :param kwargs: (``dict``) Keyword arguments to ``format()`` function.
        """
        self.out.write(' ' * self.padding + line.format(*args, **kwargs))
        self.out.write("\n")

    def print_host(self, hostname):
        """
        Prints header for new host.

        :param hostname: (``str``) Hostname to print.
        """
        self.out.write("="*79 + "\n")
        self.out.write("Host: %s\n" % hostname)
        self.out.write("="*79 + "\n")

    def produce_output(self, data):
        """
        Render and print given data.

        Data can be also instance of FormatterCommand, see documentation of
        this class for list of allowed commands.

        This shall be overridden by subclasses.

        :param data: Any value to print. Subclasses may specify their
            requirements for this argument. It can be also am instance of
            FormatterCommand.
        """
        print_line(data)

class ListFormatter(Formatter):
    """
    Base formatter taking care of list of items. It renders input data in a
    form of table with mandatory column names at the beginning followed by
    items, one occupying single line (row).

    This formatter supports following commands:
        NewHostCommand, NewTableCommand, NewTableHeadersCommand.

    The command must be provided as content of one row. This row is then not
    printed and the command is executed.

    This class should be subclassed to provide nice output.
    """
    def __init__(self, stream, padding=0):
        super(ListFormatter, self).__init__(stream, padding)
        self.want_header = True
        self.column_names = None

    def print_text_row(self, row):
        self.out.write(self.render_value(row))

    def print_row(self, data):
        """
        Print data row.

        :param data: (``tuple``) Data to print.
        """
        if self.want_header:
            self.print_header()
        self.print_text_row(data)

    def print_host(self, hostname):
        """
        Prints header for new host.

        :param hostname: (``str``) Hostname to print.
        """
        super(ListFormatter, self).print_host(hostname)
        self.want_header = True

    def print_table_title(self, title):
        """
        Prints title of next tale.

        :param title: (``str``) Title to print.
        """
        self.out.write("\n%s:\n" % title)
        self.want_header = True

    def print_header(self):
        """
        Print table header.

        :param columns: (``tuple of strings``) Column headers.
        """
        if self.column_names:
            self.print_text_row(self.column_names)
        self.want_header = False

    def produce_output(self, rows):
        """
        Prints list of rows.

        There can be a FormatterCommand instance instead of a row. See
        documentation of this class for list of allowed commands.

        :param rows: (``list or generator``) List of rows to print.
        """
        for row in rows:
            if isinstance(row, NewHostCommand):
                self.print_host(row.hostname)
            elif isinstance(row, NewTableCommand):
                self.print_table_title(row.title)
            elif isinstance(row, NewTableHeaderCommand):
                self.column_names = row.columns
            else:
                self.print_row(row)

class TableFormatter(ListFormatter):
    """
    Print nice human-readable table to terminal.

    To print the table nicely aligned, the whole table must be populated first.
    Therefore this formatter stores all rows locally and does not print
    them until the table is complete. Column sizes are computed afterwards
    and the table is printed at once.

    This formatter supports following commands:
        NewHostCommand, NewTableCommand, NewTableHeadersCommand.

    The command must be provided as content of one row. This row is then not
    printed and the command is executed.
    """
    def __init__(self, stream, padding=0):
        super(ListFormatter, self).__init__(stream, padding)
        self.stash = []

    def print_text_row(self, row, column_size):
        for i in xrange(len(row)):
            size = column_size[i]
            item = self.render_value(str(row[i]).ljust(size))
            self.out.write(item)
            self.out.write(" ")
        self.out.write("\n")

    def print_stash(self):
        if not self.stash:
            return

        # Compute column sizes
        column_sizes = []
        for i in xrange(len(self.column_names)):
            column_sizes.append(len(self.column_names[i]))
        for row in self.stash:
            for i in xrange(len(row)):
                l = len(str(row[i]))
                if column_sizes[i] < l:
                    column_sizes[i] = l

        # print headers
        self.print_text_row(self.column_names, column_sizes)
        # print stashed rows
        for row in self.stash:
            self.print_text_row(row, column_sizes)
        self.stash = []

    def print_row(self, data):
        """
        Print data row.

        :param data: (``tuple``) Data to print.
        """
        self.stash.append(data)

    def print_host(self, hostname):
        """
        Prints header for new host.

        :param hostname: (``str``) Hostname to print.
        """
        self.print_stash()
        super(TableFormatter, self).print_host(hostname)

    def print_table_title(self, title):
        """
        Prints title of next tale.

        :param title: (``str``) Title to print.
        """
        self.print_stash()
        self.out.write("\n%s:\n" % title)

    def produce_output(self, rows):
        """
        Prints list of rows.

        There can be a FormatterCommand instance instead of a row. See
        documentation of this class for list of allowed commands.

        :param rows: (``list or generator``) List of rows to print.
        """
        super(TableFormatter, self).produce_output(rows)
        self.print_stash()

class CsvFormatter(ListFormatter):
    """
    Renders data in a csv (Comma-separated values) format.

    This formatter supports following commands:
        NewHostCommand, NewTableCommand, NewTableHeadersCommand.
    """

    def render_value(self, val):
        if isinstance(val, basestring):
            if isinstance(val, unicode):
                val.encode('utf-8')
            val = '"%s"' % val.replace('"', '""')
        elif val is None:
            val = ''
        else:
            val = str(val)
        return val

    def print_text_row(self, row):
        self.print_line(",".join(self.render_value(v) for v in row))

class SingleFormatter(Formatter):
    """
    Meant to render and print attributes of single object.
    Attributes are rendered as a list of assignments of values to
    variables (attribute names).

    This formatter supports following commands:
        NewHostCommand.
    """

    def produce_output(self, data):
        """
        Render and print attributes of single item.

        There can be a FormatterCommand instance instead of a data. See
        documentation of this class for list of allowed commands.

        :param data: (``tuple`` or ``dict``) Is either a pair of property
            names with list of values or a dictionary with property names as
            keys. Using the pair allows to order the data the way it should be
            printing. In the latter case the properties will be sorted by the
            property names.
        """
        if isinstance(data, NewHostCommand):
            self.print_host(data.hostname)
            return

        if not isinstance(data, (tuple, dict)):
            raise ValueError("data must be tuple or dict")

        if isinstance(data, tuple):
            if not len(data) == 2:
                raise ValueError(
                    "data must contain: (list of columns, list of rows)")
            dataiter = itertools.izip(data[0], data[1])
        else:
            dataiter = itertools.imap(
                    lambda k: (k, self.render_value(data[k])),
                    sorted(data.keys()))
        for name, value in dataiter:
            self.print_line("{0}={1}", name, value)

class ShellFormatter(SingleFormatter):
    """
    Specialization of ``SingleFormatter`` having its output executable as a
    shell script.

    This formatter supports following commands:
        NewHostCommand.
    """

    def render_value(self, val):
        if isinstance(val, basestring):
            if isinstance(val, unicode):
                val.encode('utf-8')
            val = "'%s'" % val.replace("'", "\\'")
        elif val is None:
            val = ''
        else:
            val = str(val)
        return val

class FormatterCommand(object):
    """
    Base class for formatter commands.
    """
    pass

class NewHostCommand(FormatterCommand):
    """
    Command for formatter to finish current table (if any), print
    header for new host and (if there are any data) print table header.
    """
    def __init__(self, hostname):
        self.hostname = hostname

class NewTableCommand(FormatterCommand):
    """
    Command for formatter to finish current table (if any), print
    the 'title' and (if there are any data) print table header.
    """
    def __init__(self, title=None):
        self.title = title

class NewTableHeaderCommand(FormatterCommand):
    """
    Command for formatter to finish current table (if any), store new table
    header and (if there are any data) print the table header.
    The table header will be printed in all subsequent tables, until
    new NewTableHeaderCommand arrives.
    """
    def __init__(self, columns=None):
        self.columns = columns
