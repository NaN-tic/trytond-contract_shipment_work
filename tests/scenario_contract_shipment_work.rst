===============================
Contract Shipment Work Scenario
===============================


Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.datetime.combine(datetime.date.today(),
    ...     datetime.datetime.min.time())
    >>> tomorrow = datetime.date.today() + relativedelta(days=1)

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install account_invoice::

    >>> Module = Model.get('ir.module')
    >>> contract_module, = Module.find([
    ...     ('name', '=', 'contract_shipment_work')])
    >>> contract_module.click('install')
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']

Create tax::

    >>> tax = create_tax(Decimal('.10'))
    >>> tax.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('40')
    >>> template.cost_price = Decimal('25')
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.customer_taxes.append(tax)
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> payment_term = PaymentTerm(name='Term')
    >>> line = payment_term.lines.new(type='percent', ratio=Decimal('.5'))
    >>> delta = line.relativedeltas.new(days=20)
    >>> line = payment_term.lines.new(type='remainder')
    >>> delta = line.relativedeltas.new(days=40)
    >>> payment_term.save()

Create monthly service::

    >>> Service = Model.get('contract.service')
    >>> service = Service()
    >>> service.name = 'Service'
    >>> service.product = product
    >>> service.freq = 'monthly'
    >>> service.interval = 1
    >>> service.save()

Configure shipment work::

    >>> Sequence = Model.get('ir.sequence')
    >>> StockConfig = Model.get('stock.configuration')
    >>> stock_config = StockConfig(1)
    >>> shipment_work_sequence, = Sequence.find([
    ...     ('code', '=', 'shipment.work'),
    ...     ])
    >>> stock_config.shipment_work_sequence = shipment_work_sequence
    >>> stock_config.save()

Create a contract::

    >>> Contract = Model.get('contract')
    >>> contract = Contract()
    >>> contract.party = party
    >>> contract.start_period_date = datetime.date(today.year, 01, 01)
    >>> contract.freq = 'monthly'
    >>> contract.interval = 1
    >>> contract.first_invoice_date = datetime.date(today.year, 01, 31)
    >>> line = contract.lines.new()
    >>> line.start_date = datetime.date(today.year, 01, 01)
    >>> line.create_shipment_work = True
    >>> line.first_shipment_date = datetime.date(today.year, 01, 05)
    >>> line.service = service
    >>> line.unit_price
    Decimal('40')
    >>> contract.click('confirm')
    >>> contract.state
    u'confirmed'

Generate consumed lines::

    >>> create_shipments = Wizard('contract.create_shipments')
    >>> create_shipments.form.date = datetime.date(today.year, 02, 01)
    >>> create_shipments.execute('create_shipments')
    >>> Shipment = Model.get('shipment.work')
    >>> shipment, = Shipment.find([])
    >>> shipment.planned_date == datetime.date(today.year, 01, 05)
    True
