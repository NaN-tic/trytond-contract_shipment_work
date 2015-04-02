#:after:contract/contract:paragraph:configuracion#

Una vez seleccionado el servicio, deberemos indicar la |freq| y el |interval|
con los que queremos que se generen los albaranes de trabajo. Ambos campos
están relacionados entre sí, por lo que si queremos que los albaranes de
trabajo se generen diariamente deberemos indicar:

* |freq|: *Diariamente*.
* |interval|: *1*.

Si queremos que se generen cada cuatro días:

* |freq|: *Diariamente*.
* |interval|: *4*.

O si, por ejemplo, queremos que se generen cada 2 semanas:

* |freq|: *Semanalmente*.
* |interval|: *2*.

#:after:contract/contract:paragraph:lineas#

Por medio del campo |create| podremos indicar si queremos que de este servicio
se creen albaranes de trabajo. Una vez seleccionada la casilla nos aparecerá el
campo |first_shipment_date| donde deberemos indicar a partir de qué día
queremos que se empiecen a generar los albaranes de trabajo del servicio
prestado.


#:before:contract/contract:paragraph:asistentes#

Previamente, si hemos marcado la casilla |create| de la línea del contrato,
podremos generar los albaranes de trabajo por medio de |menu_shipment_work|.
Con ello se nos abrirá una pestaña con todos los albaranes en estado borrador,
según la periodicidad indicada.

.. |menu_shipment_work| tryref:: contract_shipment_work.menu_create_shipments/complete_name
.. |freq| field:: contract.service/freq
.. |interval| field:: contract.service/interval
.. |create| field:: contract.line/create_shipment_work
.. |first_shipment_date| field:: contract.line/first_shipment_date