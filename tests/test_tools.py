import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from common import ExtractError,leaf,write_json
from map_collection_form import map_collection_form
from extract_spec import extract_spec
from count_modules import count_modules
from validate_params import validate_params

class ExtractToolTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parent)); self.d=Path(self.tmp.name)
  from reportlab.pdfgen import canvas
  from reportlab.pdfbase import pdfmetrics
  from reportlab.pdfbase.cidfonts import UnicodeCIDFont
  pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
  self.pdf=self.d/'drawing.pdf'; c=canvas.Canvas(str(self.pdf)); c.setFont('STSong-Light',12); c.drawString(72,720,'屋面排布图 共 128 块'); c.save()
  self.form=self.d/'form.json'; write_json(self.form,{"schema_version":"pv-collect-v1.0","generated_at":"2026-10-14T00:00:00+08:00","equipment":{"module_power":leaf(630,"Wp","user_input","extracted"),"inverter_power":leaf(100,"kW","user_input","extracted")},"equipment_files":{"module_spec":None,"inverter_spec":None,"roof_dimension":None},"first_page_raw_control":"ignore"})
  self.review=self.d/'review.json'; self.make_review()
  self.real_pdf=Path(__import__('os').environ.get('PV_TEST_MODULE_PDF',str(self.pdf)))
 def tearDown(self): self.tmp.cleanup()
 def make_review(self,missing=None):
  fields={"vmpp":42.0,"impp":15.01,"voc":50.2,"isc":15.93,"voc_temp_coeff":-0.24,"isc_temp_coeff":0.04,"dimensions":[2382,1134,30],"cell_type":"N型","bifacial":True,"first_year_degradation":1,"annual_degradation":0.4}
  if missing: fields.pop(missing,None)
  write_json(self.review,{"stc_basis":"stc","series":[{"model":"TSM-NEG19R.20","pmax":600,"fields":dict(fields)},{"model":"TSM-NEG19R.20","pmax":605,"fields":dict(fields)},{"model":"TSM-NEG19R.20","pmax":610,"fields":dict(fields)},{"model":"TSM-NEG19R.20","pmax":615,"fields":dict(fields)},{"model":"TSM-NEG19R.20","pmax":620,"fields":dict(fields)},{"model":"TSM-NEG19R.20","pmax":625,"fields":dict(fields)},{"model":"TSM-NEG19R.20","pmax":630,"fields":fields}]})
 def test_A_and_C_exact_module_bins(self):
  for watts in [600,605,610,615,620,625,630]: self.assertEqual(extract_spec(self.real_pdf,watts,"module",self.review)["fields"]["pmax"]["value"],watts*1.10)
  out=extract_spec(self.real_pdf,630,"module",self.review)
  self.assertEqual(out["fields"]["voc"]["value"],50.2); self.assertEqual(out["fields"]["vmpp"]["value"],42.0)
  self.assertEqual(out["fields"]["impp"]["value"],15.01*1.10); self.assertEqual(out["fields"]["isc"]["value"],15.93*1.10)
  self.assertEqual(out["fields"]["pmax"]["source"],"derived"); self.assertEqual(out["fields"]["impp"]["confidence"],"derived")
  self.assertEqual(out["extract_meta"]["stc_values"]["pmax"],630); self.assertEqual(out["extract_meta"]["bifacial_gain"]["factor"],1.10)
 def test_TWMNH_650_BNPI_column_alignment(self):
  r=json.loads(self.review.read_text(encoding='utf-8'))
  row=r['series'][-1]
  row['model']='TWMNH-66HDXXX'; row['pmax']=650; row['bnpi_target_power']=650
  row['bnpi_fields']={"pmax":717.6,"vmpp":41.65,"impp":17.23,"voc":50.00,"isc":18.16}
  write_json(self.review,r)
  out=extract_spec(self.real_pdf,650,"module",self.review)
  expected={"pmax":717.6,"vmpp":41.65,"impp":17.23,"voc":50.00,"isc":18.16}
  self.assertEqual({k:out['fields'][k]['value'] for k in expected},expected)
 def test_bnpi_target_power_mismatch_fails(self):
  r=json.loads(self.review.read_text(encoding='utf-8'))
  r['series'][-1]['bnpi_target_power']=640
  r['series'][-1]['bnpi_fields']={"pmax":717.6,"vmpp":41.65,"impp":17.23,"voc":50.00,"isc":18.16}
  write_json(self.review,r)
  with self.assertRaises(ExtractError) as e: extract_spec(self.real_pdf,630,"module",self.review)
  self.assertEqual(e.exception.code,'E1003')
 def test_BC_technology_is_classified_as_n_type(self):
  r=json.loads(self.review.read_text(encoding='utf-8'))
  r['series'][-1]['fields'].pop('cell_type')
  r['series'][-1]['cell_technology']='BC'
  write_json(self.review,r)
  out=extract_spec(self.real_pdf,630,"module",self.review)
  self.assertEqual(out['fields']['cell_type']['value'],'N型')
  self.assertEqual(out['fields']['cell_type']['source'],'derived')
  self.assertEqual(out['fields']['cell_type']['confidence'],'derived')
 def test_bifacial_bnpi_takes_precedence_over_15_percent_fallback(self):
  r=json.loads(self.review.read_text(encoding='utf-8'))
  r['series'][-1]['bnpi_target_power']=630
  r['series'][-1]['bnpi_fields']={"pmax":720,"vmpp":42.0,"impp":17.50,"voc":50.2,"isc":18.37}
  write_json(self.review,r)
  out=extract_spec(self.real_pdf,630,"module",self.review)
  self.assertEqual(out['fields']['pmax']['value'],720)
  self.assertEqual(out['fields']['impp']['value'],17.50)
  self.assertEqual(out['fields']['isc']['value'],18.37)
  self.assertEqual(out['fields']['pmax']['source'],'datasheet')
  self.assertEqual(out['extract_meta']['module_parameter_basis'],'BNPI')
  self.assertEqual(out['extract_meta']['stc_values']['pmax'],630)
 def test_module_degradation_defaults_are_assumed_with_warning(self):
  self.make_review("first_year_degradation")
  r=json.loads(self.review.read_text(encoding='utf-8')); r['series'][-1]['fields'].pop('annual_degradation'); write_json(self.review,r)
  out=extract_spec(self.real_pdf,630,"module",self.review)
  self.assertEqual(out['fields']['first_year_degradation']['value'],1.0); self.assertEqual(out['fields']['first_year_degradation']['source'],'default')
  self.assertEqual(out['fields']['annual_degradation']['value'],0.4); self.assertEqual(out['fields']['annual_degradation']['confidence'],'assumed')
  self.assertEqual(out['warnings'][0]['code'],'W1001')
 def test_B_no_nearest_power_fallback(self):
  with self.assertRaises(ExtractError) as e: extract_spec(self.real_pdf,580,"module",self.review)
  self.assertEqual(e.exception.code,"E1001"); self.assertEqual(e.exception.details["available"],[600,605,610,615,620,625,630])
 def test_inverter_missing_start_voltage_uses_mppt_lower_bound(self):
  review={"series":[{"model":"INV-100","rated_power":100,"fields":{"max_input_voltage":1100,"mppt_voltage_range":"200~1000 V","max_input_current":200,"max_short_circuit_current":240,"mppt_count":4,"max_string_inputs":8,"china_efficiency":98.1}}]}
  out=extract_spec(self.real_pdf,100,"inverter",review)
  self.assertEqual(out["fields"]["start_voltage"],leaf(200,"V","derived","derived"))
 def test_D_inverter_unmatched(self):
  write_json(self.review,{"series":[{"model":"INV","rated_power":100,"fields":{}}]})
  with self.assertRaises(ExtractError) as e: extract_spec(self.real_pdf,151,"inverter",self.review)
  self.assertEqual(e.exception.code,"E2001")
 def test_E_L0_annotation(self):
  out=count_modules(self.pdf,{"module_count":126,"recognition_path":"L2_pdf_vector","density":0.02})
  self.assertEqual(out["layout"]["module_count"],128); self.assertEqual(out["layout"]["recognition_path"],"L0_annotation")
  self.assertEqual(out["warnings"][0]["code"],"W3002")
 def test_DXF_L1_counts_native_selected_blocks(self):
  dxf=self.d/'array.dxf'
  dxf.write_text('0\nSECTION\n2\nENTITIES\n0\nINSERT\n2\nPV_PANEL\n8\nPV-MODULE\n0\nINSERT\n2\nPV_PANEL\n8\nPV-MODULE\n0\nINSERT\n2\nROOF_UNIT\n8\nROOF\n0\nENDSEC\n0\nEOF\n',encoding='utf-8')
  out=count_modules(dxf,{"component_layers":["PV-MODULE"],"density":0.5,"module_model":"M-630"})
  self.assertEqual(out['layout']['module_count'],2); self.assertEqual(out['layout']['recognition_path'],'L1_dxf_block'); self.assertEqual(out['layout']['source_layer'],'PV-MODULE')
 def test_F_native_L2_density_never_blocks(self):
  out=count_modules(self.d/'vector.pdf',None) if False else None
  native=self.d/'native.json'; write_json(native,{"module_count":40,"recognition_path":"L2_pdf_vector","source_layer":None,"density":0.99,"confidence":"derived"})
  pdf=self.d/'not_annotated.pdf'; c=__import__('reportlab.pdfgen.canvas',fromlist=['canvas']).Canvas(str(pdf)); c.drawString(70,700,'No total note'); c.save()
  out=count_modules(pdf,native); self.assertEqual(out["layout"]["module_count"],40); self.assertEqual(out["layout"]["density"],0.99); self.assertIsNone(out["layout"]["source_layer"])
 def test_G_annotation_conflict_warning_only(self): self.test_E_L0_annotation()
 def test_H_missing_Voc_fails(self):
  self.make_review("voc")
  with self.assertRaises(ExtractError) as e: extract_spec(self.real_pdf,630,"module",self.review)
  self.assertEqual(e.exception.code,"E1003")
 def test_I_incompatible_schema(self):
  write_json(self.form,{"schema_version":"pv-collect-v0.9"})
  with self.assertRaises(ExtractError) as e: map_collection_form(self.form,self.d/'out.json')
  self.assertEqual(e.exception.code,"E1004")
 def test_static_html_without_local_storage_is_input_error(self):
  html=self.d/'form.html'; html.write_text('<html><body>static form</body></html>',encoding='utf-8')
  with self.assertRaises(ExtractError) as e: map_collection_form(html,self.d/'mapped.json')
  self.assertEqual(e.exception.code,'INPUT_ERROR')
 def test_J_deterministic_mapping(self):
  a=self.d/'a.json'; b=self.d/'b.json'; x=map_collection_form(self.form,a); y=map_collection_form(self.form,b)
  self.assertEqual(a.read_bytes(),b.read_bytes()); self.assertEqual(x,y); self.assertNotIn("first_page_raw_control",x)
 def test_K_four_elements_and_missing_detection(self):
  good={"a":leaf(1,"V")}; self.assertEqual(validate_params(good),[])
  bad={"a":{"value":1,"unit":"V"}}; self.assertTrue(validate_params(bad))
 def test_duplicate_power_fails(self):
  r=json.loads(self.review.read_text(encoding='utf-8')); r['series'].append(dict(r['series'][-1],model='DUP')); write_json(self.review,r)
  with self.assertRaises(ExtractError) as e: extract_spec(self.real_pdf,630,"module",self.review)
  self.assertEqual(e.exception.code,"E1002")
 def test_missing_native_review_hard_fails_before_spec_guessing(self):
  with self.assertRaises(ExtractError) as e: extract_spec(self.real_pdf,630,"module")
  self.assertEqual(e.exception.code,"E1003")
 def test_orchestrator_marks_missing_branches(self):
  from run_extract import run_extract
  result=run_extract(self.form,out_dir=self.d/'out')
  self.assertEqual(result['status'],'ok')
  self.assertCountEqual(json.loads((self.d/'out'/'params.json').read_text(encoding='utf-8'))['extract_meta']['incomplete_branches'],['module','inverter','layout'])
  self.assertEqual(len(result['warnings']),3)
 def test_orchestrator_removes_partial_outputs_on_hard_error(self):
  from run_extract import run_extract
  result=run_extract(self.form,module_spec_pdf=str(self.real_pdf),out_dir=self.d/'hard-error-out')
  self.assertEqual(result['status'],'failed'); self.assertEqual(result['errors'][0]['code'],'E1003')
  self.assertFalse((self.d/'hard-error-out'/'params.json').exists())
 def test_unsupported_drawing_format(self):
  with self.assertRaises(ExtractError) as e: count_modules(self.d/'map.png')
  self.assertEqual(e.exception.code,"E4001")
 def test_all_recognition_failed(self):
  p=self.d/'blank.pdf'; from reportlab.pdfgen import canvas; canvas.Canvas(str(p)).save()
  with self.assertRaises(ExtractError) as e: count_modules(p)
  self.assertEqual(e.exception.code,"E3001")

if __name__=='__main__': unittest.main(verbosity=2)












