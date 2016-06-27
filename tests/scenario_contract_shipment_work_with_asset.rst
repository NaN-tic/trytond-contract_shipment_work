=============
Sale Scenario
=============

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

Install contract_shipment_work::

    >>> Module = Model.get('ir.module')
    >>> module, = Module.find([('name', '=', 'asset_shipment_work')])
    >>> module.click('install')
    >>> module, = Module.find([('name', '=', 'asset_owner')])
    >>> module.click('install')
    >>> module, = Module.find([('name', '=', 'asset_contract')])
    >>> module.click('install')
    >>> module, = Module.find([('name', '=', 'contract_shipment_work')])
    >>> module.click('install')
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create contract user::

    >>> Group = Model.get('res.group')
    >>> contract_user = User()
    >>> contract_user.name = 'Contract'
    >>> contract_user.login = 'contract'
    >>> contract_group, = Group.find([
    ...     ('name', '=', 'Contracts Administration'),
    ...     ])
    >>> contract_user.groups.append(contract_group)
    >>> contract_user.save()

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

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.category = category
    >>> template.default_uom = unit
    >>> template.type = 'assets'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.cost_price = Decimal('8')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> product.template = template
    >>> product.save()

    >>> service_product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'service'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.list_price = Decimal('30')
    >>> template.cost_price = Decimal('10')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> service_product.template = template
    >>> service_product.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Direct')
    >>> payment_term_line = PaymentTermLine(type='remainder')
    >>> payment_term.lines.append(payment_term_line)
    >>> payment_term.save()

Create an asset::

    >>> Asset = Model.get('asset')
    >>> asset = Asset()
    >>> asset.name = 'Asset'
    >>> asset.product = product
    >>> asset_owner = asset.owners.new()
    >>> asset_owner.owner = customer
    >>> asset.save()
    >>> asset_owner.save()
    >>> asset.reload()
    >>> asset.current_owner == customer
    True


Configure shipment work::

    >>> StockConfig = Model.get('stock.configuration')
    >>> Sequence = Model.get('ir.sequence')
    >>> stock_config = StockConfig(1)
    >>> shipment_work_sequence, = Sequence.find([
    ...     ('code', '=', 'shipment.work'),
    ...     ])
    >>> stock_config.shipment_work_sequence = shipment_work_sequence
    >>> stock_config.save()


Create daily service::

    >>> Service = Model.get('contract.service')
    >>> service = Service()
    >>> service.product = service_product
    >>> service.name = 'Service'
    >>> service.freq = 'daily'
    >>> service.interval = 1
    >>> service.save()

Create a contract::

    >>> config.user = contract_user.id
    >>> Contract = Model.get('contract')
    >>> contract = Contract()
    >>> contract.party = customer
    >>> contract.start_period_date = today
    >>> contract.freq = 'monthly'
    >>> contract.interval = 1
    >>> contract.first_invoice_date = today
    >>> line = contract.lines.new()
    >>> line.service = service
    >>> line.start_date = today
    >>> line.asset = asset
    >>> line.create_shipment_work = True
    >>> line.first_shipment_date = today
    >>> contract.click('confirm')
    >>> contract.state
    u'confirmed'

Create a shipments::

    >>> create_shipments = Wizard('contract.create_shipments')
    >>> create_shipments.form.date = today + relativedelta(days=+1)
    >>> create_shipments.execute('create_shipments')
    >>> Shipment = Model.get('shipment.work')
    >>> shipments = Shipment.find([])
    >>> shipment = shipments[0]
    >>> shipment.planned_date == today.date()
    True

The asset has a maintenance planned for the same date::

    >>> asset.reload()
    >>> asset.shipments[0].planned_date == today.date()
    True
