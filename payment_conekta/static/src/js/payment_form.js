/* eslint-disable */
odoo.define('payment_conekta.payment_form', (require) => {
    "use strict";

    const ajax = require('web.ajax');
    const PaymentForm = require('payment.payment_form');

    PaymentForm.include({
        init(){
            this.$submit = $('#o_payment_form_pay');
            Conekta.setPublishableKey($('#conekta_public_key').val());
            return this._super.apply(this, arguments);
        }, start(){
            this._super.apply(this, arguments);
            // We check that the user has selected a conekta as add payment method
            const $inputs = this.$('.card .card-body input[type="radio"]:checked');
            if($inputs.length >= 1 && $inputs.eq(0).data('provider') == 'conekta'){
                this._handle_conekta_form_deactivation({currentTarget: $inputs[0]});
            }
        },
        events: _.extend(PaymentForm.prototype.events, {
            'keyup .conekta-form input[data-conekta^="card"]': '_validate_inputs_form',
        }), _handle_conekta_form_deactivation(ev){
            if(this._onConektaForm = $(ev.currentTarget).data('provider') == 'conekta'){
                this._validate_inputs_form();
            }else{
                this.$submit.prop('disabled', null);
            }
        }, _validate_inputs_form() {
            const empty_inputs = this.$('input[data-conekta^="card"]').filter(function(){
                return $(this).val() == '';
            });
            this.$submit.prop('disabled', !!empty_inputs.length ? 'disabled' : null);
        }, conekta_tokenize_card(){
            Conekta.token.create(
                this.$el,
                this.conektaSuccessResponseHandler.bind(this),
                this.conektaErrorResponseHandler.bind(this));
        }, conektaErrorResponseHandler(response){
            this.$(".card-errors").text(response.message).show();
            this.$submit.prop('disabled', 'disabled');
        }, conektaSuccessResponseHandler(token){
            const $acquirer_radio = this.$('input[type="radio"]:checked'),
            acquirer_id = $acquirer_radio.data('acquirer-id'),
            acquirer_form = this.$('#o_payment_add_token_acq_' + acquirer_id),
            partner_id = $('input[name=partner_id]').val(),
            cc_number = $('input[name=cc_number]').val();
            acquirer_form.append($("<input type='hidden' name='token_id'>").val(token.id));
            ajax.jsonRpc('/payment/conekta/s2s/create_json_3ds', 'call', {
                'token': token.id,
                'token_id': token.id,
                'acquirer_id': acquirer_id,
                'partner_id': partner_id,
                'cc_number': cc_number
            }).then((response) => {
                if (response.result == true) {
                    acquirer_form.append($("<input type='hidden' name='payment_token_id'>").val(response.id));
                    this.parentPayEvent();
                    return;
                }
                this.$form.find(".card-errors").text(response).addClass("alert alert-danger").show();
            });
        }, payEvent(ev){
            ev.preventDefault();
            this.$('.card-errors').hide();
            this.parentPayEvent = this._super.bind(this, ...arguments);
            if(this._onConektaForm){
               this.conekta_tokenize_card();
            }else{
                this._super.apply(this, arguments);
            }
        }, radioClickEvent: function (ev) {
            // radio button checked when we click on entire zone(body) of the payment acquirer
            this._super.apply(this, arguments);
            this._handle_conekta_form_deactivation(
                {currentTarget: $(ev.currentTarget).find('input[type="radio"]')}
            );
        }
    });
});
