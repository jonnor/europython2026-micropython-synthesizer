
class DictWriter:
    def __init__(self, f, fieldnames, restval='', extrasaction='raise',
                 delimiter=',', quotechar='"', lineterminator='\r\n'):
        self.f = f
        self.fieldnames = fieldnames
        self.restval = restval
        self.extrasaction = extrasaction
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.lineterminator = lineterminator

    def _quote(self, val):
        s = '' if val is None else str(val)
        if (self.delimiter in s or self.quotechar in s or
                '\n' in s or '\r' in s):
            s = s.replace(self.quotechar, self.quotechar * 2)
            s = self.quotechar + s + self.quotechar
        return s

    def writeheader(self):
        self._write_row(self.fieldnames)

    def writerow(self, rowdict):
        if self.extrasaction == 'raise':
            extra = set(rowdict.keys()) - set(self.fieldnames)
            if extra:
                raise ValueError('dict contains fields not in fieldnames: ' +
                                  ', '.join(extra))
        row = [rowdict.get(k, self.restval) for k in self.fieldnames]
        self._write_row(row)

    def writerows(self, rowdicts):
        for r in rowdicts:
            self.writerow(r)

    def _write_row(self, values):
        line = self.delimiter.join(self._quote(v) for v in values)
        self.f.write(line + self.lineterminator)
