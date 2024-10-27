from odoo import api, fields, models
from odoo.tools import safe_eval


class OdooDataSyncWizard(models.TransientModel):
    _name = 'odoo.data.sync.wizard'
    _description = 'Odoo Data Sync wizard'

    data_sync_id = fields.Many2one('odoo.data.sync', 'data sync')
    model_id = fields.Many2one('ir.model', string='Model', required=True)
    line_ids = fields.One2many('odoo.data.sync.wizard.line', 'data_sync_wizard_id', 'Related Models')
    only_main = fields.Boolean(default=True)
    main_thread = fields.Integer('Main Thread', default=1000)
    sub_thread = fields.Integer('Sub Thread', default=100)
    domain = fields.Text(default='[]', required=True)
    model_name = fields.Char(related="model_id.model", string="Model Name", readonly=True)


    @api.onchange('model_id', 'only_main')
    def onchange_selected_model_ids(self):
        if self.only_main:
            self.line_ids = False
        else:
            all_relation_tables = set(self.model_id.field_id.filtered('relation').mapped('relation'))
            all_relation_tables.add(self.model_id.model)
            all_relation_tables.remove(self.model_id.model)
            self.line_ids = False
            self.line_ids = [(0, 0, {'model_id': self.env['ir.model'].search([('model', '=', model)], limit=1).id})
                             for model in all_relation_tables]

    def process_sync_selected_models(self):
        selected_models = list(set(self.line_ids.mapped('model_id.model')))
        selected_models.append(self.model_id.model)
        domain = safe_eval.safe_eval(self.sudo().domain)
        self.data_sync_id.sync_all(list(selected_models), self.main_thread, self.sub_thread, domain)


class OdooDataSyncWizardLine(models.TransientModel):
    _name = 'odoo.data.sync.wizard.line'
    _description = 'Odoo Data Sync wizard line'

    data_sync_wizard_id = fields.Many2one('odoo.data.sync.wizard', 'data sync wizard')
    model_id = fields.Many2one('ir.model', 'Model')
