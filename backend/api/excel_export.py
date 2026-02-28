from io import BytesIO
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


HEADER_FILL = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
SUBHEADER_FILL = PatternFill(start_color='2E75B6', end_color='2E75B6', fill_type='solid')
ALT_ROW_FILL = PatternFill(start_color='D6E4F0', end_color='D6E4F0', fill_type='solid')
WHITE_FILL = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
HEADER_FONT = Font(name='Calibri', bold=True, color='FFFFFF', size=11)
TITLE_FONT = Font(name='Calibri', bold=True, size=14, color='1F4E79')
DATA_FONT = Font(name='Calibri', size=10)
THIN_BORDER = Border(
    left=Side(style='thin', color='BDD7EE'),
    right=Side(style='thin', color='BDD7EE'),
    top=Side(style='thin', color='BDD7EE'),
    bottom=Side(style='thin', color='BDD7EE'),
)


def _apply_header_row(ws, row, headers):
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = THIN_BORDER


def _auto_width(ws):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 50)


def export_distribution_report(report_data):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    _build_summary_sheet(wb, report_data)
    _build_detail_sheet(wb, report_data)
    _build_asset_sheet(wb, report_data)

    if report_data.get('budget_comparison'):
        _build_budget_comparison_sheet(wb, report_data)

    if report_data.get('yoy_comparison'):
        _build_yoy_sheet(wb, report_data)

    if report_data.get('retained_earnings'):
        _build_retained_earnings_sheet(wb, report_data)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _build_summary_sheet(wb, report_data):
    ws = wb.create_sheet('Summary')
    period = report_data['period']
    summary = report_data['summary']

    # Title
    ws.merge_cells('A1:E1')
    title_cell = ws['A1']
    title_cell.value = 'Distribution Report – Summary by Entity'
    title_cell.font = TITLE_FONT
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30

    # Period info
    period_str = f"Period: {period['type'].capitalize()}  |  Year: {period['year']}"
    if period['quarter']:
        period_str += f"  |  Q{period['quarter']}"
    if period['month']:
        from calendar import month_name
        period_str += f"  |  {month_name[period['month']]}"
    ws.merge_cells('A2:E2')
    ws['A2'] = period_str
    ws['A2'].font = Font(name='Calibri', italic=True, size=10, color='595959')
    ws['A2'].alignment = Alignment(horizontal='center')

    # Totals box
    ws['A3'] = 'Total Distributions:'
    ws['A3'].font = Font(name='Calibri', bold=True, size=11)
    ws['B3'] = float(summary['total_distributions'])
    ws['B3'].number_format = '"$"#,##0.00'
    ws['B3'].font = Font(name='Calibri', bold=True, size=11, color='1F4E79')

    ws['D3'] = 'Entities:'
    ws['D3'].font = Font(name='Calibri', bold=True, size=11)
    ws['E3'] = summary['entity_count']

    ws['D4'] = 'Assets:'
    ws['D4'].font = Font(name='Calibri', bold=True, size=11)
    ws['E4'] = summary['asset_count']

    # Headers
    headers = ['Entity Name', 'Entity Type', 'Total Received', '# Distributions', 'Top Asset']
    _apply_header_row(ws, 6, headers)
    ws.row_dimensions[6].height = 22

    row = 7
    for i, entity in enumerate(sorted(report_data['by_entity'], key=lambda x: -float(x['total_amount']))):
        fill = ALT_ROW_FILL if i % 2 == 0 else WHITE_FILL
        top_asset = ''
        if entity['by_asset']:
            top = max(entity['by_asset'], key=lambda x: float(x['total_amount']))
            top_asset = top['asset_name']
        data = [
            entity['entity_name'],
            entity['entity_type'].capitalize(),
            float(entity['total_amount']),
            entity['distribution_count'],
            top_asset,
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = DATA_FONT
            cell.fill = fill
            cell.border = THIN_BORDER
            if col == 3:
                cell.number_format = '"$"#,##0.00'
                cell.alignment = Alignment(horizontal='right')
            elif col == 4:
                cell.alignment = Alignment(horizontal='center')
        row += 1

    _auto_width(ws)
    ws.freeze_panes = 'A7'


def _build_detail_sheet(wb, report_data):
    ws = wb.create_sheet('Distribution Detail')

    ws.merge_cells('A1:G1')
    ws['A1'] = 'Distribution Detail'
    ws['A1'].font = TITLE_FONT
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 28

    headers = ['Date', 'Asset', 'Type', 'Entity', 'Amount', 'Ownership %', 'Notes']
    _apply_header_row(ws, 2, headers)

    row = 3
    for i, item in enumerate(sorted(report_data['detail'], key=lambda x: x['distribution_date'])):
        fill = ALT_ROW_FILL if i % 2 == 0 else WHITE_FILL
        data = [
            item['distribution_date'],
            item['asset_name'],
            item['distribution_type'].replace('_', ' ').title(),
            item['entity_name'],
            float(item['amount']),
            float(item['percentage']),
            '',
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = DATA_FONT
            cell.fill = fill
            cell.border = THIN_BORDER
            if col == 5:
                cell.number_format = '"$"#,##0.00'
                cell.alignment = Alignment(horizontal='right')
            elif col == 6:
                cell.number_format = '0.0000"%"'
                cell.alignment = Alignment(horizontal='right')
        row += 1

    _auto_width(ws)
    ws.freeze_panes = 'A3'


def _build_asset_sheet(wb, report_data):
    ws = wb.create_sheet('Asset Allocations')

    ws.merge_cells('A1:F1')
    ws['A1'] = 'Asset Ownership & Allocation Summary'
    ws['A1'].font = TITLE_FONT
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 28

    headers = ['Asset', 'Asset Type', 'Total Distributed', '# Distributions', 'Entity', 'Entity Share']
    _apply_header_row(ws, 2, headers)

    # Build asset -> entity breakdown from detail
    asset_entity_map = {}
    for item in report_data['detail']:
        aid = item['asset_id']
        eid = item['entity_id']
        if aid not in asset_entity_map:
            asset_entity_map[aid] = {
                'asset_name': item['asset_name'],
                'entities': {},
            }
        if eid not in asset_entity_map[aid]['entities']:
            asset_entity_map[aid]['entities'][eid] = {
                'entity_name': item['entity_name'],
                'amount': Decimal('0'),
            }
        asset_entity_map[aid]['entities'][eid]['amount'] += Decimal(item['amount'])

    asset_totals = {a['asset_id']: a for a in report_data['by_asset']}

    row = 3
    i = 0
    for asset in report_data['by_asset']:
        aid = asset['asset_id']
        entities = asset_entity_map.get(aid, {}).get('entities', {})
        for eid, edata in entities.items():
            fill = ALT_ROW_FILL if i % 2 == 0 else WHITE_FILL
            data = [
                asset['asset_name'],
                asset['asset_type'].capitalize(),
                float(asset['total_amount']),
                asset['distribution_count'],
                edata['entity_name'],
                float(edata['amount']),
            ]
            for col, val in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.font = DATA_FONT
                cell.fill = fill
                cell.border = THIN_BORDER
                if col in (3, 6):
                    cell.number_format = '"$"#,##0.00'
                    cell.alignment = Alignment(horizontal='right')
            row += 1
            i += 1

    _auto_width(ws)
    ws.freeze_panes = 'A3'


def _build_budget_comparison_sheet(wb, report_data):
    bc = report_data['budget_comparison']
    ws = wb.create_sheet('Budget vs Actual')

    ws.merge_cells('A1:F1')
    ws['A1'] = f"Budget vs Actual — {bc['budget_name']}"
    ws['A1'].font = TITLE_FONT
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 28

    # Totals row
    ws['A3'] = 'Total Budgeted:'
    ws['A3'].font = Font(name='Calibri', bold=True, size=11)
    ws['B3'] = float(bc['total_budgeted'])
    ws['B3'].number_format = '"$"#,##0.00'
    ws['C3'] = 'Total Actual:'
    ws['C3'].font = Font(name='Calibri', bold=True, size=11)
    ws['D3'] = float(bc['total_actual'])
    ws['D3'].number_format = '"$"#,##0.00'
    ws['E3'] = 'Variance:'
    ws['E3'].font = Font(name='Calibri', bold=True, size=11)
    ws['F3'] = float(bc['total_variance'])
    ws['F3'].number_format = '"$"#,##0.00'
    ws['F3'].font = Font(name='Calibri', bold=True, size=11,
                         color='ED6C02' if float(bc['total_variance']) >= 0 else '2E7D32')

    # By Entity section
    ws['A5'] = 'By Entity'
    ws['A5'].font = Font(name='Calibri', bold=True, size=12, color='1F4E79')
    headers = ['Entity', 'Budgeted', 'Actual', 'Variance', 'Variance %', 'Status']
    _apply_header_row(ws, 6, headers)

    row = 7
    for i, item in enumerate(bc.get('by_entity', [])):
        fill = ALT_ROW_FILL if i % 2 == 0 else WHITE_FILL
        variance = float(item['variance'])
        data = [
            item['entity_name'],
            float(item['budgeted']),
            float(item['actual']),
            variance,
            f"{item['variance_pct']}%" if item['variance_pct'] else 'N/A',
            'Over' if variance >= 0 else 'Under',
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = DATA_FONT
            cell.fill = fill
            cell.border = THIN_BORDER
            if col in (2, 3, 4):
                cell.number_format = '"$"#,##0.00'
                cell.alignment = Alignment(horizontal='right')
        row += 1

    # By Asset section
    row += 1
    ws.cell(row=row, column=1, value='By Asset').font = Font(name='Calibri', bold=True, size=12, color='1F4E79')
    row += 1
    headers = ['Asset', 'Budgeted', 'Actual', 'Variance', 'Variance %', 'Status']
    _apply_header_row(ws, row, headers)
    row += 1

    for i, item in enumerate(bc.get('by_asset', [])):
        fill = ALT_ROW_FILL if i % 2 == 0 else WHITE_FILL
        variance = float(item['variance'])
        data = [
            item['asset_name'],
            float(item['budgeted']),
            float(item['actual']),
            variance,
            f"{item['variance_pct']}%" if item['variance_pct'] else 'N/A',
            'Over' if variance >= 0 else 'Under',
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = DATA_FONT
            cell.fill = fill
            cell.border = THIN_BORDER
            if col in (2, 3, 4):
                cell.number_format = '"$"#,##0.00'
                cell.alignment = Alignment(horizontal='right')
        row += 1

    _auto_width(ws)
    ws.freeze_panes = 'A7'


def _build_yoy_sheet(wb, report_data):
    yoy = report_data['yoy_comparison']
    ws = wb.create_sheet('Year over Year')

    ws.merge_cells('A1:F1')
    ws['A1'] = f"Year-over-Year Comparison — {yoy['prior_year']} vs {yoy['current_year']}"
    ws['A1'].font = TITLE_FONT
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 28

    # Totals
    ws['A3'] = f"{yoy['prior_year']} Total:"
    ws['A3'].font = Font(name='Calibri', bold=True, size=11)
    ws['B3'] = float(yoy['total_prior'])
    ws['B3'].number_format = '"$"#,##0.00'
    ws['C3'] = f"{yoy['current_year']} Total:"
    ws['C3'].font = Font(name='Calibri', bold=True, size=11)
    ws['D3'] = float(yoy['total_current'])
    ws['D3'].number_format = '"$"#,##0.00'
    ws['E3'] = 'Change:'
    ws['E3'].font = Font(name='Calibri', bold=True, size=11)
    ws['F3'] = float(yoy['total_change'])
    ws['F3'].number_format = '"$"#,##0.00'

    # By Entity
    ws['A5'] = 'By Entity'
    ws['A5'].font = Font(name='Calibri', bold=True, size=12, color='1F4E79')
    headers = ['Entity', f'{yoy["prior_year"]}', f'{yoy["current_year"]}', 'Change ($)', 'Change (%)', 'Trend']
    _apply_header_row(ws, 6, headers)

    row = 7
    for i, item in enumerate(yoy.get('by_entity', [])):
        fill = ALT_ROW_FILL if i % 2 == 0 else WHITE_FILL
        change = float(item['change'])
        data = [
            item['entity_name'],
            float(item['prior_amount']),
            float(item['current_amount']),
            change,
            f"{item['change_pct']}%" if item['change_pct'] else 'N/A',
            '↑' if change > 0 else ('↓' if change < 0 else '→'),
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = DATA_FONT
            cell.fill = fill
            cell.border = THIN_BORDER
            if col in (2, 3, 4):
                cell.number_format = '"$"#,##0.00'
                cell.alignment = Alignment(horizontal='right')
        row += 1

    # By Asset
    row += 1
    ws.cell(row=row, column=1, value='By Asset').font = Font(name='Calibri', bold=True, size=12, color='1F4E79')
    row += 1
    headers = ['Asset', f'{yoy["prior_year"]}', f'{yoy["current_year"]}', 'Change ($)', 'Change (%)', 'Trend']
    _apply_header_row(ws, row, headers)
    row += 1

    for i, item in enumerate(yoy.get('by_asset', [])):
        fill = ALT_ROW_FILL if i % 2 == 0 else WHITE_FILL
        change = float(item['change'])
        data = [
            item['asset_name'],
            float(item['prior_amount']),
            float(item['current_amount']),
            change,
            f"{item['change_pct']}%" if item['change_pct'] else 'N/A',
            '↑' if change > 0 else ('↓' if change < 0 else '→'),
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = DATA_FONT
            cell.fill = fill
            cell.border = THIN_BORDER
            if col in (2, 3, 4):
                cell.number_format = '"$"#,##0.00'
                cell.alignment = Alignment(horizontal='right')
        row += 1

    _auto_width(ws)
    ws.freeze_panes = 'A7'


def _build_retained_earnings_sheet(wb, report_data):
    re_data = report_data['retained_earnings']
    ws = wb.create_sheet('Retained Earnings')

    ws.merge_cells('A1:E1')
    ws['A1'] = f"Retained Earnings Rollforward — {re_data['year']}"
    ws['A1'].font = TITLE_FONT
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 28

    # Summary totals
    ws['A3'] = 'Beginning Balance:'
    ws['A3'].font = Font(name='Calibri', bold=True, size=11)
    ws['B3'] = float(re_data['total_beginning_balance'])
    ws['B3'].number_format = '"$"#,##0.00'
    ws['C3'] = f'{re_data["year"]} Distributions:'
    ws['C3'].font = Font(name='Calibri', bold=True, size=11)
    ws['D3'] = float(re_data['total_current_year'])
    ws['D3'].number_format = '"$"#,##0.00'

    ws['A4'] = 'Ending Balance:'
    ws['A4'].font = Font(name='Calibri', bold=True, size=11, color='1F4E79')
    ws['B4'] = float(re_data['total_ending_balance'])
    ws['B4'].number_format = '"$"#,##0.00'
    ws['B4'].font = Font(name='Calibri', bold=True, size=11, color='1F4E79')

    headers = ['Entity', 'Beginning Balance', f'{re_data["year"]} Distributions', 'Ending Balance']
    _apply_header_row(ws, 6, headers)

    row = 7
    for i, item in enumerate(re_data.get('by_entity', [])):
        fill = ALT_ROW_FILL if i % 2 == 0 else WHITE_FILL
        data = [
            item['entity_name'],
            float(item['beginning_balance']),
            float(item['current_year_distributions']),
            float(item['ending_balance']),
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = DATA_FONT
            cell.fill = fill
            cell.border = THIN_BORDER
            if col in (2, 3, 4):
                cell.number_format = '"$"#,##0.00'
                cell.alignment = Alignment(horizontal='right')
        row += 1

    # Totals row
    fill = PatternFill(start_color='E3F2FD', end_color='E3F2FD', fill_type='solid')
    bold = Font(name='Calibri', bold=True, size=10)
    totals = [
        'Total',
        float(re_data['total_beginning_balance']),
        float(re_data['total_current_year']),
        float(re_data['total_ending_balance']),
    ]
    for col, val in enumerate(totals, 1):
        cell = ws.cell(row=row, column=col, value=val)
        cell.font = bold
        cell.fill = fill
        cell.border = THIN_BORDER
        if col in (2, 3, 4):
            cell.number_format = '"$"#,##0.00'
            cell.alignment = Alignment(horizontal='right')

    _auto_width(ws)
    ws.freeze_panes = 'A7'
