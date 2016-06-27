# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import datetime
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule
from sql.aggregate import Max

from trytond.model import fields, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If, Bool
from trytond.transaction import Transaction
from trytond.tools import reduce_ids
from trytond.wizard import Wizard, StateView, StateAction, Button

from trytond.modules.contract.contract import RRuleMixin

__all__ = ['ContractService', 'CreateShipmentsStart', 'CreateShipments',
    'ContractLine', 'ShipmentWork', 'ShipmentWorkProduct']
__metaclass__ = PoolMeta


def todatetime(date):
    return datetime.datetime.combine(date, datetime.datetime.min.time())


class ContractService(RRuleMixin):
    __name__ = 'contract.service'

    work_description = fields.Text('Work Desctiption', translate=True)

    @classmethod
    def __setup__(cls):
        super(ContractService, cls).__setup__()
        cls._rec_name = 'name'  # Avoid overringind rec_name from Mixin

    def rrule_values(self):
        values = super(ContractService, self).rrule_values()
        return values


class ShipmentWork:
    __name__ = 'shipment.work'

    # TODO: Maybe origin could be better.
    contract_line = fields.Many2One('contract.line', 'Contract Line',
        select=True)


class ShipmentWorkProduct:
    __name__ = 'shipment.work.product'

    def get_sale_line(self, sale, invoice_method):
        line = super(ShipmentWorkProduct, self).get_sale_line(sale,
            invoice_method)
        if not line:
            return
        if hasattr(self.shipment, 'asset'):
            line.asset = self.shipment.asset
        return line


class ContractLine:
    __name__ = 'contract.line'

    last_work_shipment_date = fields.Function(fields.Date(
            'Last Work Shipment Date'), 'get_last_work_shipment_date')

    create_shipment_work = fields.Boolean('Create Shipments?')
    first_shipment_date = fields.Date('First Shipment Date',
        states={
            'required': Bool(Eval('create_shipment_work')),
            'invisible': ~Bool(Eval('create_shipment_work')),
            }, depends=['create_shipment_work'])

    @classmethod
    def get_last_work_shipment_date(cls, lines, name):
        pool = Pool()
        Shipment = pool.get('shipment.work')
        table = Shipment.__table__()
        cursor = Transaction().cursor
        line_ids = [l.id for l in lines]
        values = dict.fromkeys(line_ids, None)
        cursor.execute(*table.select(table.contract_line,
                    Max(table.planned_date),
                where=reduce_ids(table.contract_line, line_ids),
                group_by=table.contract_line))
        values.update(cursor.fetchall())
        return values

    def get_shipment_works(self, end_date):
        shipment_works = []
        if not self.create_shipment_work or self.service.freq is None:
            return shipment_works

        start_date = self.last_work_shipment_date or self.first_shipment_date
        rs = self.service.rrule
        r = rrule(rs._freq, interval=rs._interval, dtstart=start_date,
            until=self.contract.end_date)
        for date in r.between(todatetime(start_date),
                todatetime(end_date), inc=True):
            shipment_work = self.get_shipment_work(date.date())
            shipment_works.append(shipment_work)
        return shipment_works

    def get_shipment_work(self, planned_date):
        pool = Pool()
        ShipmentWork = pool.get('shipment.work')
        shipment = ShipmentWork()
        shipment.party = self.contract.party
        shipment.planned_date = planned_date
        shipment.contract_line = self
        shipment.work_description = self.service.work_description
        if self.contract.party.customer_payment_term:
            shipment.payment_term = self.contract.party.customer_payment_term
        if hasattr(self, 'asset'):
            shipment.asset = self.asset
            # Compatibilty with aset_zone module:
            if hasattr(self.asset, 'zone') and self.asset.zone and \
                    self.asset.zone.employee:
                shipment.employees = [self.asset.zone.employee]
        return shipment

    @classmethod
    def create_shipment_works(cls, lines, date=None):
        'Create shipment works until date'
        pool = Pool()
        ShipmentWork = pool.get('shipment.work')

        to_create = []
        for line in lines:
            shipment_works = line.get_shipment_works(date)
            if shipment_works:
                to_create += shipment_works

        return ShipmentWork.create([w._save_values for w in to_create])


class CreateShipmentsStart(ModelView):
    'Create Shipments Start'
    __name__ = 'contract.create_shipments.start'
    date = fields.Date('Date')

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()


class CreateShipments(Wizard):
    'Create Shipments'
    __name__ = 'contract.create_shipments'
    start = StateView('contract.create_shipments.start',
        'contract_shipment_work.create_shipments_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('OK', 'create_shipments', 'tryton-ok', True),
            ])
    create_shipments = StateAction('shipment_work.act_shipment_work')

    def do_create_shipments(self, action):
        pool = Pool()
        ContractLine = pool.get('contract.line')
        lines = ContractLine.search([])

        shipments = ContractLine.create_shipment_works(lines,
            self.start.date + relativedelta(days=+1))
        data = {'res_id': [c.id for c in shipments]}
        if len(shipments) == 1:
            action['views'].reverse()
        return action, data
