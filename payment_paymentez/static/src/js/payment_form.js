odoo.define('payment_paymentez.payment_form', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var PaymentForm = require('payment.payment_form');

var qweb = core.qweb;
var _t = core._t;
ajax.loadXML('/payment_paymentez/static/src/xml/payment_paymentez_templates.xml', qweb);
var paymentCheckout = {};
PaymentForm.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * called when clicking on pay now or add payment event to create token for credit card/debit card.
     *
     * @private
     * @param {Event} ev
     * @param {DOMElement} checkedRadio
     * @param {Boolean} addPmEvent
     */
    _openPaymentModal: function (ev, $checkedRadio, addPmEvent) {
        var self = this;
        if (ev.type === 'submit') {
            var button = $(ev.target).find('*[type="submit"]')[0]
        } else {
            var button = ev.target;
        }
        //this.disableButton(button);
        var acquirer_id = this.getAcquirerIdFromRadio($checkedRadio);
        var acquirerForm = this.$('#o_payment_form_acq_' + acquirer_id);
        var inputsForm = $('input', acquirerForm);
        var formData = self.getFormData(inputsForm);
        console.log("this.options.orderId", this.options.orderId);
        if (this.options.orderId === undefined) {
            console.warn('payment_form: unset order_id when adding new token; things could go wrong');
        }

        this._rpc({
            route: '/payment/paymentez/get_credentials_api',
            params: {
                'acquirer_id': acquirer_id,
                'order_id': this.options.orderId
            }
        }).then(function(token){
            if(token.result === true || token.result === "True"){
                self._initPaymentCheckout(ev, self, token.client_app_code, token.client_app_key, token.env_mode, acquirer_id);
                return token;
            }else{
                self.enableButton(button);
                self.displayError(
                    _t('Error al obtener datos de conexión de Paymentez')                
                );
                return token;
            }
        }).then(function(token) {
            if (token.result === true) {
                //console.log("token", token);
                paymentCheckout.open({
                    user_id: token.user_id,
                    user_email: token.user_email, //optional
                    user_phone: token.user_phone, //optional
                    order_description: token.order_description,
                    order_amount: token.order_amount,
                    order_vat: token.order_vat,
                    order_reference: token.order_reference,  
                    order_taxable_amount: token.order_taxable_amount,
                    order_tax_percentage: token.order_tax_percentage   
                });
                var divblockUI = $('div.blockOverlay');
                console.log("divblockUI", divblockUI);
                //fix error de bloqueo de pantalla
                divblockUI.remove();
            };
        });       
    },
    /**
     * called when clicking on pay now or add payment event to create token for credit card/debit card.
     *
     * @private
     * @param {String} client_app_code
     * @param {String} client_app_key
     * @param {String} env_mode
     */
    _initPaymentCheckout: function (ev, self, app_code, app_key, env_mode, acquirer_id) {
    paymentCheckout = new PaymentCheckout.modal({
        client_app_code: app_code, // Client Credentials
        client_app_key: app_key, // Client Credentials
        locale: 'es', // User's preferred language (es, en, pt). English will be used by default.
        env_mode: env_mode, // `prod`, `stg`, `local` to change environment. Default is `stg`
        onOpen: function () {
            console.log('modal open');
            var divblockUI = $('div.blockOverlay');
            console.log("divblockUI", divblockUI);
            //fix error de bloqueo de pantalla
            divblockUI.remove();
            $('body').unblock();
            console.log("Desbloquea UI");
        },
        onClose: function () {
          var button = $('#o_payment_form_pay[type="submit"]')[0];
          self.enableButton(button);
          console.log('modal closed');
        },
        onResponse: function (response) { // The callback to invoke when the Checkout process is completed
            var acquirerForm = this.$('form[provider="paymentez"]');
            var inputsForm = $('input', acquirerForm);
            var formData = self.getFormData(inputsForm);
            console.log('formData',formData);
            self._rpc({
                route: '/payment/paymentez/capture',
                params: {
                    "acquirer_id": acquirer_id,
                    "reference": formData.reference,
                    'order_id': formData.sale_order_id,
                    "response": response
                }
            }).then(function (data) {
                if(data.result === true ){
                    window.location.href = data.url;
                }else{
                    self.enableButton(button);
                    self.displayError(
                        _t('Error al procesar pago')                
                    );
                }
            });
        }
      });
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * @override
     */
    payEvent: function (ev) {
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a stripe as s2s payment method
        if ($checkedRadio.length === 1 && $checkedRadio.data('provider') === 'paymentez') {
            this._openPaymentModal(ev, $checkedRadio);
            return this._super.apply(this, arguments);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * @override
     */
    addPmEvent: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a stripe as add payment method
        if ($checkedRadio.length === 1 && $checkedRadio.data('provider') === 'paymentez') {
            this._openPaymentModal(ev, $checkedRadio, true);
            return this._super.apply(this, arguments);
        } else {
            return this._super.apply(this, arguments);
        }
    },
});
});
