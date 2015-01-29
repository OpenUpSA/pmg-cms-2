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
    def __init__(self, org_list):
        self.org_list = org_list
        self.formats = {}

    def build(self):
        """
        Generate an Excel spreadsheet and return it as a string.
        """
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output)

        self.formats['date'] = workbook.add_format({'num_format': 'yyyy/mm/dd'})
        self.formats['bold'] = workbook.add_format({'bold': True})

        self.organisations_worksheet(workbook)

        workbook.close()
        output.seek(0)

        return output.read()

    def organisations_worksheet(self, wb):
        ws = wb.add_worksheet('Active organisations')
        tmp = organisations_to_excel(self.org_list)
        self.write_table(ws, 'Active organisations', tmp)

    def write_table(self, ws, name, rows, keys=None, rownum=0, colnum=0):
        if rows:
            keys = rows[0]
            data = rows[1::]

            ws.add_table(rownum, colnum, rownum+len(rows), colnum+len(keys)-1, {
                'name': name,
                'columns': [{'header': k} for k in keys],
                'data': data,
                })

        return len(rows)+1