# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import datetime
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule
from sql.aggregate import Max
from sql import Cast, Literal
from sql.functions import Substring, Position

from trytond.model import fields, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If, Bool
from trytond.transaction import Transaction
from trytond.tools import reduce_ids
from trytond.wizard import Wizard, StateView, StateAction, Button

from trytond.modules.contract.contract import RRuleMixin

__all__ = ['ContractService', 'CreateShipmentsStart', 'CreateShipments',
    'ContractLine', 'ShipmentWork', 'ShipmentWorkProduct', 'Asset']
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

    contract = fields.Function(fields.Many2One('contract', 'Contract'),
        'get_contract', searcher='search_contract')

    def get_contract(self, name):
        return (self.origin and self.origin.contract and
            self.origin.contract.id or None)

    @classmethod
    def search_contract(cls, name, clause):
        print [('origin.contract',) + tuple(clause[1:])]
        return [('origin.contract',) + tuple(clause[1:])]

    @classmethod
    def _get_origin(cls):
        res = super(ShipmentWork, cls)._get_origin()
        return res + ['contract.line']

    @fields.depends('asset', 'employees')
    def on_change_asset(self):
        if self.asset:
            if (hasattr(self.asset, 'zone') and self.asset.zone and
                    self.asset.zone.employee):
                self.employees = [self.asset.zone.employee.id]
            if self.asset.current_owner:
                self.party = self.asset.current_owner.id


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

class Contract:
    __name__ = 'contract'

    shipment_works = fields.Function(fields.One2Many(
        'shipment.work', None, 'Shipment Works'), 'get_shipment_works')

    @classmethod
    def get_shipment_works(cls, contracts, name):
        pool = Pool()
        ContractLine = pool.get('contract.line')
        ShipmentWork = pool.get('contract.shipment.work')

        contract_line = ContractLine.__table__()
        shipment_work = ShipmentWork.__table__()

        cursor = Transaction().connection.cursor()
        table = cls.__table__()
        contract_ids = [x.id for x in contracts]
        res = dict().fromkeys(contract_ids, [])

        origin_id = Cast(Substring(shipment_work.origin,
            Position(',', shipment_work.origin) +
            Literal(1)), cls.id.sql_type().base)
        origin_model = Substring(shipment_work.origin,
            0, Position(',', shipment_work.origin))

        query = table.join(contract_line, 'LEFT',
            condition=table.id == contract_line.contract
            ).join(shipment_work, 'LEFT',
                condition=((contract_line.id == origin_id) &
                    (origin_model == 'contract.line'))
            ).select(table.id, shipment_work.id,
                where=reduce_ids(table.id, contract_ids),
            )

        cursor.execute(*query)
        for contract, shipment_work in cursor.fetchall():
            res[contract].append(shipment_work)
        return res

        @classmethod
        def get_cost_and_revenue(cls, contracts, names):
            res = super(Contract, cls).get_cost_and_revenue(contracts, names)
            for contract in contracts:
                for shipment in contract.shipment_works:
                    if shipment.state != 'done':
                        continue
                    if 'cost' in names:
                        res['cost'][contract.id] += shipment.cost
                    if 'revenue' in names:
                        res['revenue'][contract.id] += shipment.cost
            return res


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
    shipment_works = fields.One2Many('shipment.work', 'origin',
        'ShipmentWork')

    @classmethod
    def get_cost_and_revenue(cls, lines, names):
        res = super(ContractLine, cls).get_cost_and_revenue(lines, names)

        for line in lines:
            for shipment in line.shipment_works:
                if shipment.state != 'done':
                    continue
                if 'cost' in names:
                    res['cost'][line.id] += shipment.cost
                if 'revenue' in names:
                    res['revenue'][line.id] += shipment.cost
        return res

    @classmethod
    def get_last_work_shipment_date(cls, lines, name):
        pool = Pool()
        Shipment = pool.get('shipment.work')
        table = Shipment.__table__()
        cursor = Transaction().connection.cursor()
        line_ids = [l.id for l in lines]
        values = dict.fromkeys(line_ids, None)
        cursor.execute(*table.select(table.origin,
                    Max(table.planned_date),
                where=reduce_ids(
                    Cast(Substring(table.origin, Position(',', table.origin) +
                        Literal(1)), cls.id.sql_type().base),
                    line_ids),
                group_by=table.origin))
        values.update(cursor.fetchall())
        return values

    @classmethod
    def get_shipment_works(cls, lines, end_date):
        shipment_works = []
        dates = cls.get_last_work_shipment_date(lines, None)

        for line in lines:
            last_work_shipment = dates.get(line.id)
            start_date = last_work_shipment or line.first_shipment_date
            rs = line.service.rrule
            r = rrule(rs._freq, interval=rs._interval, dtstart=start_date,
                until=line.contract.end_date)
            for date in r.between(todatetime(start_date),
                    todatetime(end_date), inc=True):
                shipment_work = line.get_shipment_work(date.date())
                shipment_works.append(shipment_work)
        return shipment_works

    def get_shipment_work(self, planned_date):
        pool = Pool()
        ShipmentWork = pool.get('shipment.work')
        shipment = ShipmentWork()
        shipment.party = self.contract.party
        shipment.planned_date = planned_date
        shipment.origin = self
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

        shipment_works = cls.get_shipment_works(lines, date)
        return ShipmentWork.create([w._save_values for w in shipment_works])

    @classmethod
    def get_totals(cls, lines, names):
        res = super(ContractLine, cls).get_totals(lines, names)



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
        lines = ContractLine.search([
            ('service.freq', '!=', None),
            ('contract.state', '=', 'confirmed'),
            ('create_shipment_work', '=', True)])

        shipments = ContractLine.create_shipment_works(lines,
            self.start.date + relativedelta(days=+1))
        data = {'res_id': [c.id for c in shipments]}
        if len(shipments) == 1:
            action['views'].reverse()
        return action, data


class Asset:
    __name__ = 'asset'

    shipments = fields.One2Many('shipment.work', 'asset', 'Work Shipments')
