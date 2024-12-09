import xmlrpc.client
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
from odoo.osv import expression
import pprint
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)


class IrModel(models.Model):
    _inherit = 'ir.model'

    def _compute_display_name(self):
        super(IrModel, self)._compute_display_name()
        for record in self:
            if self.env.context.get('from_data_sync_model'):
                record.display_name = record.model

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        if self.env.context.get('from_data_sync_model'):
            domain = [('model', 'ilike', name)]
        return super(IrModel, self)._name_search(name, domain, operator, limit, order)


class OdooDataSync(models.Model):
    _name = 'odoo.data.sync'
    _description = 'Synchronize Odoo Data from Another Odoo Instance Dynamically'

    source_url = fields.Char('Source URL', required=True)
    source_db = fields.Char('Source Database', required=True)
    source_username = fields.Char('Source Username', required=True)
    source_password = fields.Char('Source Password', required=True)

    cache_data = defaultdict(dict)

    def open_data_sync_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Data Sync',
            'res_model': 'odoo.data.sync.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_data_sync_id': self.id}
        }

    def sync_all(self, selected_model_ids, main_thread, sub_thread, domain, only_create):
        for model in selected_model_ids:
            _logger.info(f"Syncing model ::::::::::::::::::: {model}")
            self._sync_model(model, main_batch_size=main_thread, sub_batch_size=sub_thread, search_domain=domain, only_create=only_create)
            _logger.info(f"completed Syncing model ::::::::::::::: {model}")


    def _connect_to_source(self):
        """
        Establish connection to the source Odoo instance via XML-RPC.
        """
        try:
            common = xmlrpc.client.ServerProxy(f'{self.source_url}/xmlrpc/2/common')
            uid = common.authenticate(self.source_db, self.source_username, self.source_password, {})
            if not uid:
                raise ValidationError("Authentication failed!")
            models_server = xmlrpc.client.ServerProxy(f'{self.source_url}/xmlrpc/2/object')
            return models_server, uid
        except Exception as e:
            raise ValidationError(f"Error connecting to source: {str(e)}")

    def _get_model_fields(self, model_name):
        """
        Retrieve all fields dynamically for the given model.
        """
        return self.env['ir.model.fields'].search([
            ('model', '=', model_name),
            ('ttype', 'not in', ('binary', 'image', 'reference')),
            ('store', '=', True),
        ])

    def _sync_related_records(self, related_ids, related_model, field_type, match_field):
        all_fields = self._get_model_fields(related_model)
        if match_field not in all_fields.mapped('name'):
            return False
        if not related_ids:
            return False
        if field_type == 'o2m':
            synced_ids = []
            for related_id in related_ids:
                domain_require = [(match_field, '=', related_id)]
                if 'active' in all_fields:
                    domain_require.append(('active', 'in', [False, True]))
                if not self.cache_data[related_model].get(related_id):
                    synced_record = self.env[related_model].search(domain_require, limit=1)
                else:
                    synced_record = self.cache_data[related_model][related_id]
                if synced_record:
                    self.cache_data[related_model][related_id] = synced_record
                    synced_ids.append(synced_record.id)
            return [(6, 0, synced_ids)] if synced_ids else False
        if field_type == 'm2o':
            domain_require = [(match_field, '=', related_ids[0])]
            if 'active' in all_fields:
                domain_require.append(('active', 'in', [False, True]))
            if not self.cache_data[related_model].get(related_ids[0]):
                synced_record = self.env[related_model].search(domain_require, limit=1)
            else:
                synced_record = self.cache_data[related_model][related_ids[0]]
            if synced_record:
                return synced_record.id
        return False


    def _sync_model(self, model_name, local_model=False, search_domain=False, match_field='x_old_id_custom', main_batch_size=1000, sub_batch_size=100, only_create=False):
        """
        Generic method to sync any model from the source to the current instance dynamically.
        """
        if not search_domain:
            search_domain = []
        if not local_model:
            local_model = model_name
        models_server, uid = self._connect_to_source()
        # try:
        # Fetch all field names dynamically
        all_fields = self._get_model_fields(model_name)
        if match_field not in all_fields.mapped('name'):
            self.env['ir.model.fields'].create({
                'name': match_field,
                'model_id': self.env['ir.model'].search([('model', '=', model_name)]).id,
                'field_description': 'Old ID',
                'ttype': 'char',
                'store': True
            })
        server_fields = models_server.execute_kw(self.source_db, uid, self.source_password, model_name,'fields_get', [])
        if 'active' in all_fields.mapped('name'):
            search_domain = expression.AND([search_domain, [('active', 'in', [True, False])]])
        if 'company_id' in all_fields.mapped('name'):
            search_domain = expression.AND([search_domain, ["|", ('company_id', '!=', False),  ('company_id', '=', False)]])
        fields_to_sync = [fl for fl in all_fields.mapped('name') if fl in tuple(server_fields.keys())]
        m2o_fields = all_fields.filtered(lambda x: x.ttype == 'many2one').mapped('name')
        o2m_fields = all_fields.filtered(lambda y: y.ttype in ('one2many', 'many2many')).mapped('name')

        # Fetch records from the source
        record_ids = models_server.execute_kw(self.source_db, uid, self.source_password, model_name, 'search', [search_domain])
        if not record_ids:
            _logger.info(f"No {model_name} records found in source.")
            return

        records = models_server.execute_kw(self.source_db, uid, self.source_password,
                                           model_name, 'read', [record_ids], {'fields': fields_to_sync})

        for i in range(0, len(records), main_batch_size):
            spited_records = records[i:i + main_batch_size]
            create_vals = []
            for record in spited_records:
                old_id = int(record['id'])
                print(f"=============importing=======>{old_id}")
                # Check if the record already exists in the target instance
                if not self.cache_data[local_model].get(old_id):
                    local_record = self.env[local_model].search([(match_field, '=', old_id)], limit=1)
                    self.cache_data[local_model][old_id] = local_record
                else:
                    local_record = self.cache_data[local_model][old_id]

                # Sync related O2M and M2M fields dynamically
                for field in fields_to_sync:
                    related_model = self.env[local_model]._fields[field].comodel_name
                    if field in m2o_fields:
                        value_to_pass = self._sync_related_records(record[field], related_model, 'm2o', match_field)
                        del record[field]
                        if value_to_pass:
                            record[field] = value_to_pass
                    if field in o2m_fields:
                        value_to_pass = self._sync_related_records(record[field], related_model, 'o2m', match_field)
                        del record[field]
                        if value_to_pass:
                            record[field] = value_to_pass
                if local_record:
                    if only_create:
                        continue
                    vals_write = {field: record[field] for field in fields_to_sync if
                                  field in record and field in fields_to_sync}
                    local_record.write(vals_write)
                else:
                    vals_create = {field: record[field] for field in fields_to_sync if
                                   field in record and field != 'id'}
                    vals_create[match_field] = old_id
                    create_vals.append(vals_create)

            #flush current write queue to the target instance before creating new records to avoid data loss on february ;)
            self.env[local_model]._flush()

            # Create new records in the target instance
            for xx in range(0, len(create_vals), sub_batch_size):
                print(f"=====================xx========>{xx}")
                self.env[local_model].create(create_vals[xx:xx+sub_batch_size])
                self.env[local_model]._flush()

        # except Exception as e:
        #     error_details = pprint.pformat(str(e))
        #     raise ValidationError(f"Error syncing {model_name}: {str(error_details)}")
