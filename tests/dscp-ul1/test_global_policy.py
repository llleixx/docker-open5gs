import copy,importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("global_policy",ROOT/"scripts/dscp-global-policy.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class GlobalPolicyTest(unittest.TestCase):
 def setUp(self):
  self.base={"pcf":{}}
  self.sub={"imsi":"460880000009901","slice":[]}
  for n in range(1,4):
   self.sub["slice"].append({"sst":1,"sd":f"{n:06d}","default_indicator":n==1,"session":[{"name":f"slice{n}","type":3,"ue":{"ipv4":f"10.0.{n}.1"},"ambr":{"uplink":{"value":1,"unit":3},"downlink":{"value":1,"unit":3}},"qos":{"index":9,"arp":{"priority_level":8,"pre_emption_capability":1,"pre_emption_vulnerability":1}}}]})
 def test_current_and_future_supi_have_identical_policy(self):
  other=copy.deepcopy(self.sub);other["imsi"]="460889999999999"
  self.assertEqual(module.global_policy(self.base,[self.sub]),module.global_policy(self.base,[other]))
 def test_dscp_only_and_unchanged_other_dnns(self):
  cfg=module.global_policy(self.base,[self.sub]);pol=cfg["pcf"]["policy"][0]
  self.assertNotIn("supi_range",pol);self.assertEqual(len(pol["slice"]),3)
  for index,sl in enumerate(pol["slice"]):
   session=sl["session"][0];before=self.sub["slice"][index]["session"][0]
   self.assertNotIn("ue",session)
   for key in ["type","qos","ambr"]:self.assertEqual(session[key],before[key])
   if index:
    self.assertNotIn("pcc_rule",session)
   else:
    self.assertEqual([x["qos"]["index"] for x in session["pcc_rule"]],[6,8])
    for rule in session["pcc_rule"]:
     self.assertEqual(rule["flow"][0]["description"],"permit out ip from any to assigned")
     self.assertEqual(rule["flow"][0]["direction"],2)
 def test_nonuniform_defaults_rejected(self):
  other=copy.deepcopy(self.sub);other["slice"][0]["session"][0]["ambr"]["uplink"]["value"]=2
  with self.assertRaises(ValueError):module.global_policy(self.base,[self.sub,other])
 def test_existing_policy_rejected(self):
  with self.assertRaises(ValueError):module.global_policy({"pcf":{"policy":[{"existing":True}]}},[self.sub])
if __name__=="__main__":unittest.main()
