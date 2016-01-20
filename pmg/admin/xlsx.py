import xlsxwriter
import StringIO


def organisations_to_excel(org_list):

    headings = [
        "Organisation",
        "Domain",
        "Number of active users",
    ]

    list_out = [headings, ]
    # assemble list of organisations
    for org in org_list:
        cells = []
        cells.append(org[0])
        cells.append(org[1])
        cells.append(org[2])
        list_out.append(cells)
    return list_out


class XLSXBuilder:
    def __init__(self):
        self.formats = {}

    def from_orgs(self, org_list):
        output, wb = self.new_workbook()

        ws = wb.add_worksheet('Active organisations')
        tmp = organisations_to_excel(org_list)
        self.write_table(ws, tmp)

        wb.close()
        output.seek(0)

        return output.read()

    def from_resultset(self, rows):
        output, wb = self.new_workbook()

        ws = wb.add_worksheet('Results')

        data = [rows.keys()] + [[r[k] for k in rows.keys()] for r in rows]
        self.write_table(ws, data)

        wb.close()
        output.seek(0)

        return output.read()

    def new_workbook(self):
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output)

        self.formats['date'] = workbook.add_format({'num_format': 'yyyy/mm/dd'})
        self.formats['bold'] = workbook.add_format({'bold': True})

        return output, workbook

    def write_table(self, ws, rows, rownum=0, colnum=0):
        if rows:
            keys = rows[0]
            data = rows[1:]

            ws.add_table(0, colnum, rownum + len(rows) - 1, colnum + len(keys) - 1, {
                'columns': [{'header': k} for k in keys],
                'data': data,
            })

        return len(rows) + 1
