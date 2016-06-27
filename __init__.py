# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .contract import *


def register():
    Pool.register(
        ContractService,
        CreateShipmentsStart,
        ContractLine,
        ShipmentWork,
        ShipmentWorkProduct,
        module='contract_shipment_work', type_='model')
    Pool.register(
        CreateShipments,
        module='contract_shipment_work', type_='wizard')
