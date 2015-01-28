import xlsxwriter
import StringIO


def users_to_excel(users):

    headings = [
        "Username",
        "Organisation",
        "Email",
        ]

    list_out = [headings, ]
    for user in users:
        cells = []
        cells.append(user.name)
        if user.organisation:
            cells.append(user.organisation.name)
        else:
            cells.append("")
        cells.append(user.email)
        list_out.append(cells)
    return list_out


def organisations_to_excel(users):

    headings = [
        "Organisation",
        ]

    list_out = [headings, ]
    # assemble list of organisations
    organisations = []
    for user in users:
        if user.organisation and not user.organisation in organisations:
            organisations.append(user.organisation)
    for organisation in organisations:
        cells = []
        cells.append(organisation.name)
        list_out.append(cells)
    return list_out


class XLSXBuilder:
    def __init__(self, users):
        self.users = users
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
        self.users_worksheet(workbook)

        workbook.close()
        output.seek(0)

        return output.read()

    def organisations_worksheet(self, wb):
        ws = wb.add_worksheet('Active organisations')
        tmp = organisations_to_excel(self.users)
        self.write_table(ws, 'Active organisations', tmp)

    def users_worksheet(self, wb):
        ws = wb.add_worksheet('Active users')
        tmp = users_to_excel(self.users)
        self.write_table(ws, 'Active users', tmp)

    def write_table(self, ws, name, rows, keys=None, rownum=0, colnum=0):
        if rows:
            keys = rows[0]
            data = rows

            ws.add_table(rownum, colnum, rownum+len(rows), colnum+len(keys)-1, {
                'name': name,
                'columns': [{'header': k} for k in keys],
                'data': data,
                })

        return len(rows)+1