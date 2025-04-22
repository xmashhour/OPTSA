import calendar
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

from .project_worksite import PROJECT_WORKSITE_TYPE


def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = int(source_date.year + month / 12)
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def subtract_month(date_a, year=0, month=0):
    year, month = divmod(year * 12 + month, 12)
    if date_a.month <= month:
        year = date_a.year - year - 1
        month = date_a.month - month + 12
    else:
        year = date_a.year - year
        month = date_a.month - month
    return date_a.replace(year=year, month=month)


class Contract(models.Model):
    _name = "property.contract"
    _description = "Property Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def _default_security_deposit_account(self):
        return int(self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.security_deposit_account"))

    def _default_income_account(self):
        return int(self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.income_account"))

    # rental_contract Info
    name = fields.Char("Name", size=64, default='New')
    origin = fields.Char("Source Document", size=64)

    contract_type = fields.Selection([('is_rental', 'Rental'), ('is_ownership', 'Ownership')], default='is_rental')

    type = fields.Selection(selection=PROJECT_WORKSITE_TYPE + [('shop', 'Shop')], string="Property Type")
    user_id = fields.Many2one("res.users", "Salesman", default=lambda self: self.env.user)
    partner_id = fields.Many2one("res.partner", "Tenant OR Owner", required=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)

    date = fields.Date("Date", default=fields.Date.context_today)
    date_from = fields.Date("Start Date", required=True, default=fields.Date.context_today)
    date_to = fields.Date("End Date", required=True)
    date_payment = fields.Date("First Payment Date", default=fields.Date.context_today)
    apply_tax = fields.Boolean("Apply Tax")

    attachment_line_ids = fields.One2many("attachment.line", "contract_id", "Documents")
    reservation_id = fields.Many2one("property.reservation", "Reservation")
    paid = fields.Float(compute="_check_amounts", string="Paid")
    balance = fields.Float(compute="_check_amounts", string="Balance", )
    amount_total = fields.Float(compute="_check_amounts", string="Total", )

    # Project Info
    project_id = fields.Many2one("project.worksite", related="reservation_id.project_id", store=True)
    project_code = fields.Char("Code", related="project_id.default_code", store=True)

    # Property Unit Info
    property_id = fields.Many2one("product.template", "Property", copy=False, required=True,
                                  domain=[("is_property", "=", True), ("state", "=", "free")])
    property_code = fields.Char("Property Code", related="property_id.default_code", store=True)
    property_area = fields.Float("Property Area", related="property_id.property_area", store=True)
    price_per_m = fields.Float("Base Price", related="property_id.price_per_m", store=True)
    floor = fields.Integer("Floor", related="property_id.floor", store=True)
    address = fields.Char("Address", related="property_id.address", store=True)

    insurance_fee = fields.Integer("Insurance fee", required=True)
    rental_fee = fields.Float("Rental fee", compute="_compute_rental_fee", digits=(16, 4), store=True)

    loan_line_ids = fields.One2many("loan.line", "contract_id")
    region_id = fields.Many2one("region.region", "Region")
    state = fields.Selection([("draft", "Draft"), ("confirmed", "Confirmed"), ("renew", "Renewed"),
                              ("cancel", "Canceled")], "Status", default=lambda *a: "draft")

    account_income = fields.Many2one("account.account", "Income Account", default=_default_income_account)
    account_security_deposit = fields.Many2one("account.account", "Security Deposit Account",
                                               default=_default_security_deposit_account)

    voucher_count = fields.Integer("Voucher Count", compute="_voucher_count")
    entry_count = fields.Integer("Entry Count", compute="_entry_count")

    periodicity = fields.Selection([("days", "Days"), ("weeks", "Weeks"), ("months", "Months"), ("years", "Years")],
                                   string="Recurrence", required=True, default="months", tracking=True,
                                   help="Invoice automatically repeat at specified interval")
    recurring_interval = fields.Integer(string="Invoicing Period", help="Repeat every (Days/Week/Month/Year)",
                                        required=True, default=1, tracking=True)

    deposit = fields.Float("Deposit")
    rental_agreement = fields.Selection(selection=[("per_sft", "Per SFT"), ("fixed", "Fixed Amount")],
                                        default="per_sft")

    increment_recurring_interval = fields.Integer("Increment Recurring Interval")
    increment_period = fields.Selection([("months", "Months"), ("years", "Years")],
                                        string="Increment Recurrence", required=True, default="years", tracking=True)
    increment_percentage = fields.Float("Increment Percentage")

    # Project Info
    pricing = fields.Float("Price", required=True, digits="Product Price")
    template_id = fields.Many2one("installment.template", "Payment Template")

    maintenance = fields.Float(string="Maintenance", digits="Product Price")
    date_maintenance = fields.Date("Date Maintenance")
    maintenance_type = fields.Selection([("percentage", "Percentage"), ("amount", "Amount")])

    advance_payment_type = fields.Selection([("percentage", "Percentage"), ("amount", "Amount")],
                                            "Advance Payment Type")
    advance_payment = fields.Float("Advance Payment Value")
    advance_payment_date = fields.Date("Advance Payment Date")
    advance_payment_journal_id = fields.Many2one("account.journal", string="Advance Payment Journal")
    advance_payment_payment_id = fields.Many2one("account.payment", string="Advance Payment")

    @api.depends("loan_line_ids.amount", "loan_line_ids.amount_residual")
    def _check_amounts(self):
        total_paid = 0
        total_non_paid = 0
        amount_total = 0
        for rec in self:
            for line in rec.loan_line_ids:
                amount_total += line.amount
                total_non_paid += line.amount_residual
                total_paid += line.amount - line.amount_residual

            rec.paid = sum(rec.loan_line_ids.filtered(lambda x: x.payment_state == 'paid').mapped('amount'))
            rec.balance = total_non_paid
            rec.amount_total = amount_total

    def _voucher_count(self):
        voucher_obj = self.env["account.payment"]
        voucher_ids = voucher_obj.search([("real_estate_ref", "ilike", self.name)])
        self.voucher_count = len(voucher_ids)

    def _entry_count(self):
        move_obj = self.env["account.move"]
        move_ids = move_obj.search([("rental_id", "in", self.ids)])
        self.entry_count = len(move_ids)

    def auto_rental_invoice(self):
        try:
            rental_pool = self.env["loan.line"]
            rental_line_ids = rental_pool.search([("contract_id.state", "=", "confirmed"),
                                                  ("date", "<=", fields.Date.today())])
            account_move_obj = self.env["account.move"]
            journal_pool = self.env["account.journal"]
            journal = journal_pool.search([("type", "=", "sale")], limit=1)

            for line in rental_line_ids:
                if not line.invoice_id:
                    inv_dict = {
                        "journal_id": journal.id,
                        "partner_id": line.contract_id.partner_id.id,
                        "move_type": "out_invoice",
                        "rental_line_id": line.id,
                        "invoice_date_due": line.date,
                        "ref": (line.contract_id.name + " - " + line.name),
                    }

                    vals = {
                        "name": (line.contract_id.name + " - " + line.name),
                        "quantity": 1,
                        "price_unit": line.amount,
                    }

                    if line.contract_id.apply_tax:
                        tax_ids = [(6, 0, self.env.company.account_sale_tax_id.ids,)]
                        vals.update({"tax_ids": tax_ids})

                    inv_dict["invoice_line_ids"] = [(0, None, vals)]
                    invoice = account_move_obj.create(inv_dict)
                    invoice.action_post()
                    line.invoice_id = invoice.id
        except:
            return "Internal Error"

    @api.depends("price_per_m", "property_area", "rental_agreement")
    def _compute_rental_fee(self):
        for rec in self:
            if rec.rental_agreement == "per_sft":
                rec.rental_fee = (rec.price_per_m or 1) * (rec.property_area or 1)
            else:
                rec.rental_fee = rec.price_per_m

    @api.constrains("recurring_interval")
    def _check_recurring_interval(self):
        for record in self:
            if record.recurring_interval <= 0:
                raise ValidationError(_("The recurring interval must be positive"))

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
            raise ValidationError(_("Contract start date must be less than contract end date."))

    @api.onchange("date_from", "date_to", "rental_fee", "insurance_fee", "periodicity", "recurring_interval",
                  "increment_percentage", "increment_period", "increment_recurring_interval", "increment_percentage")
    def action_calculate(self):
        self.prepare_lines()

    @api.onchange("region_id")
    def onchange_region(self):
        if self.region_id:
            project_ids = self.env["project.worksite"].search([("region_id", "=", self.region_id.id)])
            projects = []
            for u in project_ids:
                projects.append(u.id)
            return {"domain": {"property_id": [("id", "in", projects)]}}

    @api.onchange("project_id")
    def onchange_project(self):
        if self.project_id:
            proper_ids = self.env["product.template"].search([("is_property", "=", True),
                                                              ("project_worksite_id", "=", self.project_id.id),
                                                              ("state", "=", "free")])
            property_ids = []
            for u in proper_ids:
                property_ids.append(u.id)

            project_obj = self.env["project.worksite"].browse(self.project_id.id)
            region = project_obj.region_id.id
            owner = project_obj.partner_id.id
            if project_obj:
                return {
                    "value": {"region": region, "partner_id": owner},
                    "domain": {"property_id": [("id", "in", property_ids)]},
                }

    @api.onchange("property_id")
    def onchange_unit(self):
        self.type = self.property_id.project_type
        self.project_id = self.property_id.project_worksite_id.id
        self.region_id = self.property_id.region_id.id
        self.rental_fee = self.property_id.rental_fee
        self.insurance_fee = self.property_id.insurance_fee

    def generate_entries(self):
        journal_pool = self.env["account.journal"]
        journal = journal_pool.search([("type", "=", "sale")], limit=1)
        if not journal:
            raise UserError(_("Please set sales accounting journal!"))
        account_move_obj = self.env["account.move"]
        total = 0
        for rec in self:
            if not rec.partner_id.property_account_receivable_id:
                raise UserError(_("Please set receivable account for partner!"))
            if not rec.account_income:
                raise UserError(_("Please set income account for this contract!"))
            if rec.insurance_fee and not rec.account_security_deposit:
                raise UserError(_("Please set security deposit account for this contract!"))

            for line in rec.loan_line_ids:
                total += line.amount
            if total <= 0:
                raise UserError(_("Invalid Rental Amount!"))

            account_move_obj.create({
                "ref": rec.name, "journal_id": journal.id, "rental_id": rec.id,
                "line_ids": [
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.partner_id.property_account_receivable_id.id,
                        "debit": total,
                        "credit": 0.0}),
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.account_income.id,
                        "debit": 0.0,
                        "credit": (total - rec.insurance_fee),
                    }),
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.account_security_deposit.id,
                        "debit": 0.0,
                        "credit": rec.insurance_fee,
                    }),
                ]})

    def prepare_lines(self):
        rental_lines = []
        self.loan_line_ids = None
        for rec in self:
            if rec.periodicity and rec.date_from and rec.date_to:
                i = 1
                date_from = rec.date_from
                date_to = rec.date_to

                if self.insurance_fee:
                    rental_lines.append((0, 0, {
                        "serial": i,
                        "amount": self.insurance_fee,
                        "date": date_from,
                        "name": _("Insurance Deposit")
                    }))
                    i += 1

                rental_fee = rec.rental_fee
                new_date = date_from

                rental_lines.append((0, 0, {
                    "serial": i,
                    "amount": rental_fee,
                    "date": date_from,
                    "name": _("Rental Fee"),
                }))
                i += 1
                incr_new_date = date_from
                periodicity = self.periodicity
                increment_period = self.increment_period

                incr_new_date = incr_new_date + relativedelta(**{increment_period: self.increment_recurring_interval})

                while new_date < (date_to - relativedelta(**{periodicity: self.recurring_interval})):
                    new_date = new_date + relativedelta(**{periodicity: self.recurring_interval})

                    if incr_new_date <= new_date:
                        incr_new_date = incr_new_date + relativedelta(
                            **{increment_period: self.increment_recurring_interval})

                        rental_fee += (rental_fee * self.increment_percentage) / 100

                    rental_lines.append((0, 0, {
                        "serial": i,
                        "amount": rental_fee,
                        "date": new_date,
                        "name": _("Rental Fee"),
                    }))
                    i += 1
                self.write({"loan_line_ids": rental_lines})

    # Ownership Contract
    @api.onchange("template_id", "date_payment", "pricing", "advance_payment", "advance_payment_type")
    def onchange_tmpl(self):
        for rec in self:
            if rec.template_id:
                rec.loan_line_ids = False
                rec.loan_line_ids = rec._prepare_lines(rec.date_payment)

    @api.onchange("reservation_id")
    def onchange_reservation(self):
        self.project_id = self.reservation_id.project_id.id
        self.region_id = self.reservation_id.region_id.id
        self.partner_id = self.reservation_id.partner_id.id
        self.property_id = self.reservation_id.property_id.id
        self.address = self.reservation_id.address
        self.floor = self.reservation_id.floor
        self.pricing = self.reservation_id.net_price
        self.date_payment = self.reservation_id.date_payment
        self.template_id = self.reservation_id.template_id.id
        self.type = self.reservation_id.type
        self.property_area = self.reservation_id.property_area
        if self.template_id:
            self.loan_line_ids = self._prepare_lines(self.date_payment)

    def action_receive_deposit(self):
        if not self.advance_payment_journal_id:
            raise UserError(_("Please set the Advance Payment Journal!"))
        if not self.advance_payment_date:
            raise UserError(_("Please set the Advance Payment Date!"))
        pricing = self.pricing
        custom_adv_payment = (self.advance_payment if self.advance_payment_type == "amount"
                              else (pricing * (self.advance_payment / 100)))
        rec = self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "amount": custom_adv_payment,
            "partner_id": self.partner_id.id,
            "date": self.advance_payment_date,
        })
        rec.action_post()
        self.advance_payment_payment_id = rec.id

    def _prepare_lines(self, date_payment):
        self.loan_line_ids = None
        loan_lines = []
        if self.template_id:
            ind = 1
            pricing = self.pricing
            custom_adv_payment = (self.advance_payment if self.advance_payment_type == "amount" else (
                    pricing * (self.advance_payment / 100)))

            if custom_adv_payment > 0:
                pricing -= custom_adv_payment
                loan_lines.append((0, 0, {
                    "name": _("Contract"),
                    "serial": ind,
                    "journal_id": self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.income_journal"),
                    "amount": custom_adv_payment,
                    "date": date_payment,
                }))
                ind += 1

            mon = self.template_id.duration_month
            yr = self.template_id.duration_year
            repetition = self.template_id.repetition_rate
            advance_percent = self.template_id.adv_payment_rate
            deduct = self.template_id.deduct
            if not date_payment:
                raise UserError(_("Please select first payment date!"))
            adv_payment = pricing * float(advance_percent) / 100
            if mon > 12:
                x = mon / 12
                mon = (x * 12) + mon % 12
            mons = mon + (yr * 12)
            if adv_payment:
                loan_lines.append((0, 0, {
                    "name": _("Advance Payment"),
                    "serial": ind,
                    "journal_id": int(
                        self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.income_journal")),
                    "amount": adv_payment,
                    "date": date_payment,
                }))
                ind += 1
                if deduct:
                    pricing -= adv_payment

            loan_amount = (pricing / float(mons or 1)) * repetition
            m = 0
            while m < mons:
                loan_lines.append((0, 0, {
                    "name": _("Loan Installment"),
                    "serial": ind,
                    "journal_id": int(
                        self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.income_journal")),
                    "amount": loan_amount,
                    "date": date_payment,

                }))
                ind += 1
                date_payment = add_months(date_payment, int(repetition))
                m += repetition

            if self.maintenance:
                loan_lines.append((0, 0, {
                    "name": _("Maintenance"),
                    "serial": ind,
                    "journal_id": int(
                        self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.maintenance_journal")),
                    "amount": self.maintenance
                    if self.maintenance_type == "amount"
                    else self.pricing * (self.maintenance / 100),
                    "date": self.date_maintenance,
                }))
                ind += 1

        return loan_lines

    def action_confirm(self):
        for contract_id in self:

            if contract_id.contract_type == 'is_rental':
                contract_id.name = self.env["ir.sequence"].next_by_code("rental.contract")

            if contract_id.contract_type == "is_ownership":
                contract_id.name = self.env["ir.sequence"].next_by_code("ownership.contract")

            contract_id.property_id.write({"state": "on_lease"})
        self.write({"state": "confirmed"})

    def action_cancel(self):
        for contract_obj in self:
            contract_obj.property_id.write({"state": "free"})
            contract_obj.write({"state": "cancel"})

            for line in contract_obj.loan_line_ids:
                line.invoice_id.button_draft()
                line.invoice_id.button_cancel()

    def unlink(self):
        if self.state != "draft":
            raise UserError(_("You can not delete a contract not in draft state"))
        super(Contract, self).unlink()

    def view_vouchers(self):
        vouchers = []
        voucher_obj = self.env["account.payment"]
        voucher_ids = voucher_obj.search([("real_estate_ref", "=", self.name)])
        for obj in voucher_ids:
            vouchers.append(obj.id)

        return {
            "name": _("Receipts"),
            "domain": [("id", "in", vouchers)],
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "account.payment",
            "type": "ir.actions.act_window",
            "view_id": False,
            "target": "current",
        }

    def view_entries(self):
        entries = []
        entry_obj = self.env["account.move"]
        entry_ids = entry_obj.search([("rental_id", "in", self.ids)])
        for obj in entry_ids:
            entries.append(obj.id)

        return {
            "name": _("Journal Entries"),
            "domain": [("id", "in", entries)],
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "view_id": False,
            "target": "current",
        }

    def create_move(self, rec, debit, credit, move, account):
        move_line_obj = self.env["account.move.line"]
        move_line_obj.create({
            "name": rec.name,
            "partner_id": rec.partner_id.id,
            "account_id": account,
            "debit": debit,
            "credit": credit,
            "move_id": move,
        })

    def generate_cancel_entries(self):
        journal_pool = self.env["account.journal"]
        journal = journal_pool.search([("type", "=", "sale")], limit=1)
        if not journal:
            raise UserError(_("Please set sales accounting journal!"))
        account_move_obj = self.env["account.move"]
        total = 0
        for rec in self:
            if not rec.partner_id.property_account_receivable_id:
                raise UserError(_("Please set receivable account for partner!"))

            if not rec.account_income:
                raise UserError(_("Please set income account for this contract!"))

            for line in rec.loan_line_ids:
                total += line.amount

            account_move_obj.create({
                "ref": rec.name,
                "journal_id": journal.id,
                "rental_id": rec.id,
                "line_ids": [
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.partner_id.property_account_receivable_id.id,
                        "debit": 0.0,
                        "credit": total,
                    }),
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.account_income.id,
                        "debit": total,
                        "credit": 0.0,
                    }),
                ],
            })
