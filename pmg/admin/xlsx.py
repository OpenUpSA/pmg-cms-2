import xlsxwriter
import io


class XLSXBuilder:
    def __init__(self):
        self.formats = {}

    def from_orgs(self, org_list):
        output, wb = self.new_workbook()

        ws = wb.add_worksheet("Active organisations")

        rows = [["Organisation", "Domain", "Number of active users"]]
        rows += [org[0:3] for org in org_list]
        self.write_table(ws, rows)

        wb.close()
        output.seek(0)

        return output.read()

    def from_resultset(self, rows):
        output, wb = self.new_workbook()

        ws = wb.add_worksheet("Results")

        data = [list(rows.keys())] + [[r[k] for k in list(rows.keys())] for r in rows]
        self.write_table(ws, data)

        wb.close()
        output.seek(0)

        return output.read()

    def new_workbook(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        self.formats["date"] = workbook.add_format({"num_format": "yyyy/mm/dd"})
        self.formats["bold"] = workbook.add_format({"bold": True})

        return output, workbook

    def write_table(self, ws, rows, rownum=0, colnum=0):
        if rows:
            keys = rows[0]
            data = rows[1:]

            ws.add_table(
                0,
                colnum,
                rownum + len(rows) - 1,
                colnum + len(keys) - 1,
                {"columns": [{"header": k} for k in keys], "data": data,},
            )

        return len(rows) + 1
