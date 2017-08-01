import json
import sys
from pg import DB
import marshal
from multiprocessing.dummy import Pool as ThreadPool
from collections import defaultdict
import ast
import random,string

tmp_utils = None

class data_utils(object):
	"""docstring for db_utils"""
	def __init__(self, arg):
		#super(db_utils, self).__init__()
		self.arg = arg
		self.db = DB(dbname='structnet', user='structnet', passwd='structnet', host='localhost')
		#self.identity = ''.join(random.choice(string.ascii_lowercase) for _ in range(8))
		#print self.identity
		print "Conncted!"

	def load_pmids(self):
		f = open(self.arg['corpus_map'],'rb')
		self.pmid_dict = marshal.load(f)
		f.close()
		print "PMID loaded!"

	def insert_prediction(self):
		cnt = 0
		# 527.8M lines
		with open(self.arg['data_file'], 'r') as IN:
			for line in IN:
				#try:
				if cnt % 50000 == 0:
					print self.arg['data_file'],"process ", cnt, " lines"
				cnt+=1
				tmp=json.loads(line)
				self.db.insert(self.arg['prediction_table'], entity_a=tmp['em1Text'], entity_b=tmp['em2Text'],
				relation_type=tmp['label'], score=tmp['score'])

	def insert_query(self):
		with open(self.arg['data_file']) as IN:
			line_num=0
			for line in IN:
				print line_num
				tmp=line.split('\t')
				target_type = ast.literal_eval(tmp[0])[0]
				if '[' in tmp[3]:
					output_types = ast.literal_eval(tmp[3])
				else:
					output_types = [tmp[3]]
				relation_type = tmp[2]
				self.db.insert(self.arg['query_table'], target_type=target_type, output_types=output_types,
					index=line_num, relation_type=relation_type)
				line_num += 1


	def insert_caseolap(self,index_number):
		with open(self.arg['data_file']+str(index_number)+'_c.txt') as IN:
			for line in IN:
				tmp=line.split('\t')
				score_list=tmp[1].strip().lstrip('[').rstrip(']').split(',')
				for ele in score_list:
					temp=ele.strip().split('|')
					if len(temp)!=2:
						continue
					self.db.insert(self.arg['caseolap_table'], doc_id=index_number, sub_type=tmp[0],
				entity=temp[0], score=float(temp[1]))
	
	def query_prediction(self, name_a, name_b,relation_type):
		self.db.query("set statement_timeout TO 0")
		query_string = "SELECT score FROM "+self.arg['prediction_table']+" WHERE entity_a=\'" + name_a +"\' AND entity_b=\'" + \
		name_b + "\' AND relation_type=\'" + relation_type + "\'"
		#query_em_a = "SELECT sent_id FROM"+self.arg['entity_table']+" WHERE entity_name=\'"+name_a+"\' GROUP BY article_id"
		q = self.db.query(query_string)
		if len(q.dictresult()) == 0:
			return 0
		else:
			return q.dictresult()[0]['score']

	def query_prediction_v2(self, name_a, name_b,relation_type):
		query_string = "SELECT score FROM "+self.arg['prediction_table']+" WHERE entity_a=\'" + name_a +"\' AND entity_b=\'" + \
		name_b + "\' AND relation_type=\'" + relation_type + "\'"
		
		query_ems = "SELECT L.article_title, L.pmid, L.sent FROM entity_table as L INNER JOIN (select sent_id FROM entity_table where entity_name=\'"+name_a+\
			"\') AS R ON L.sent_id=R.sent_id where entity_name=\'"+name_b+"\' LIMIT 1"
		#set_a = set(map(lambda x:x['sent_id'], self.db.query(query_em_a).dictresult()))
		##query_em_b = "SELECT distinct sent_id FROM entity_table WHERE entity_name=\'"+name_b+"\'"
		#set_b = set(map(lambda x:x['sent_id'], self.db.query(query_em_b).dictresult()))
		#print set_a.intersection(set_b)
		self.db.query("set statement_timeout TO 5000")
		try:
			result = self.db.query(query_ems).dictresult()[0]
		except:
			result = {}
		q = self.db.query(query_string)
		if len(q.dictresult()) == 0:
			result['score'] = 0
		else:
			result['score'] = q.dictresult()[0]['score']
		return result
		#print query_string

	def query_distinctive(self,target_type,output_types,relation_type, sub_types,num_records=8):
		self.db.query("set statement_timeout TO 0")
		sub_types = ast.literal_eval(sub_types)
		result=[]
		query_string = "SELECT index FROM query_table WHERE target_type @@ \'" + target_type + "\' AND output_types@>\'" +\
		output_types+"\' and relation_type=\'" + relation_type +"\'"
		#print query_string
		idx = self.db.query(query_string).dictresult()[0]['index']
		for sub_type in sub_types:
			query_string = "SELECT entity,score FROM " + self.arg['caseolap_table'] + " WHERE doc_id=" + str(idx) + \
			" AND sub_type @@ \'" + sub_type + "\' ORDER BY score LIMIT " + str(num_records)
			q = self.db.query(query_string)
			result.append(q.dictresult())
		return result

	def query_distinctive_v2(self,target_type,output_types,relation_type, sub_types,num_records=8):
		self.db.query("set statement_timeout TO 0")
		sub_types = ast.literal_eval(sub_types)
		result=[]
		pmid_result = []
		query_string = "SELECT index FROM query_table WHERE target_type @@ \'" + target_type + "\' AND output_types@>\'" +\
		output_types+"\' and relation_type=\'" + relation_type +"\'"
		#print query_string
		if 'MeSH' in target_type:
			type_b_name = 'type_b_mesh'
		else:
			type_b_name = 'type_b_umls'
		
		if 'MeSH' in output_types:
			type_a_name = 'type_a_mesh'
		else:
			type_a_name = 'type_a_umls'
		idx = self.db.query(query_string).dictresult()[0]['index']
		for sub_type in sub_types:
			query_string = "SELECT entity,score FROM " + self.arg['caseolap_table'] + " WHERE doc_id=" + str(idx) + \
			" AND sub_type @@ \'" + sub_type + "\' ORDER BY score LIMIT " + str(num_records)
			q = self.db.query(query_string)
			
			type_target = sub_type.split('::')[0]
			#print type_target
			#entity_list = q.dictresult()
			pmids=[]
			for em in q.dictresult():
				qq = "select pmid from entity_table where sent_id = (select sent_id FROM relation_table WHERE entity_a=\'" +em['entity'] +\
				"\' AND relation_type = '"+relation_type+"' LIMIT 1) LIMIT 1"
				#"\' AND relation_type = '"+relation_type+"' AND "+type_b_name+"@>'{"+type_target+"}' LIMIT 1"
				em_result  = self.db.query(qq).dictresult()
				if len(em_result) > 0:
					em_result[0]['entity'] = em['entity']
					pmids.append(em_result[0])
			result.append(q.dictresult())
			pmid_result.append(pmids)
		return result,pmid_result

	def insert_record(self):
		cnt = 0
		# 527.8M lines
		with open(self.arg['data_file'], 'r') as IN:
			for line in IN:
				#try:
				if cnt % 5000 == 0:
					print self.arg['data_file'],"process ", cnt, " lines"
				cnt += 1
				tmp=json.loads(line)
				type_dict = {}
				for e in tmp['entityMentions']:
					aid = str(tmp['articleId'])
					mesh = []
					umls = []
					go = []
					sub_type = defaultdict(list)
					for l in e['label']:
						if 'MeSH' in l:
							mesh.append(l.replace('MeSH:::', ''))
						elif 'GO' in l:
							go.append(l.replace('GO:::', ''))
						else:
							umls.append(l)
					if len(go) > 0:
						sub_type['go'] = True
					else:
						sub_type['go'] = False
					if len(mesh) > 0:
						sub_type['mesh'] = mesh[0].split('::')
					sub_type['umls'] = umls
					type_dict[e['start']] = sub_type

					assert(len(self.pmid_dict[aid])<9)
					self.db.insert(self.arg['entity_table'], entity_name=e['text'], sent_id=tmp['sentId'],
						article_id=tmp['articleId'], pmid=self.pmid_dict[aid][0], 
						article_title=self.pmid_dict[aid][1], sent=tmp['sentText'])
				for r in tmp['relationMentions']:
					self.db.insert(self.arg['relation_table'], entity_a=r['em1Text'], entity_b=r['em2Text'],
						relation_type=r['label'], a_is_gene=type_dict[r['em1Start']]['go'],
						b_is_gene=type_dict[r['em2Start']]['go'], type_a_umls=type_dict[r['em1Start']]['umls'],
						type_b_umls=type_dict[r['em2Start']]['umls'], type_a_mesh=type_dict[r['em1Start']]['mesh'],
						type_b_mesh=type_dict[r['em2Start']]['mesh'], sent_id=tmp['sentId'], article_id=tmp['articleId'])
				#except:
					#print cnt

	def generate_random_walks(self, edge_pairs, num_walks=3, num_steps=3):
		print len(edge_pairs)
		outgoing_edges = defaultdict(list)
		ingoing_edges = defaultdict(list)
		map(lambda x:outgoing_edges[x['entity_a']].append(x['entity_b']), edge_pairs)
		map(lambda x:ingoing_edges[x['entity_b']].append(x['entity_a']), edge_pairs)
		for k,v in outgoing_edges.iteritems():
			if len(v) > 0:
				v.append(k)
		#print outgoing_edges
		#print ingoing_edges
		#print outgoing_edges
		temp = max(outgoing_edges.values(), key=len)
		origin = temp[-1]
		walk_nodes = [origin]
		total_nodes = set([origin])
		edges = set()
		for i in xrange(num_steps):
			#print "++++++++++++++++++++",i
			next_step = []
			while len(walk_nodes) > 0:
				node = walk_nodes.pop()
				if i % 2 == 0:
					node_list = outgoing_edges[node][:-1]
					assert(len(node_list) > 0)
				else:
					node_list = ingoing_edges[node]
					assert(len(node_list) > 0)
				#print node
				if len(node_list) <= num_walks:
					next_step.extend(node_list)
					edges = edges.union(list(map(lambda x: (node,x),node_list)))
				else:
					#print "random_sample",node_list
					random_nodes = random.sample(node_list, num_walks)
					next_step.extend(random_nodes)
					edges = edges.union(list(map(lambda x: (node,x),random_nodes)))
			assert(len(walk_nodes)==0)
			walk_nodes = list(set(next_step))
			total_nodes = total_nodes.union(set(next_step))
		#print total_nodes
		print len(edges)
		return edges
		#print edges


	def query_links_with_walk(self, type_a, type_b, relation_type, num_edges=5, num_pps=1):
		try:
			type_a = ast.literal_eval(type_a)
			type_b = ast.literal_eval(type_b)
		except:
			pass
		#print num_edges
		#query_string = "SELECT * FROM (SELECT DISTINCT ON(entity_a,entity_b) entity_a,entity_b,sent_id  "+"FROM "+self.arg['relation_table']+" WHERE type_a_"+type_a['name']+"@>'"\
		#+type_a['type']+"' AND type_b_"+type_b['name']+"@>'"+ type_b['type']+"' AND relation_type='"+relation_type + "') x ORDER BY RANDOM() LIMIT 500"
		query_string = "SELECT * FROM (SELECT entity_a,entity_b,(array_agg('[' || article_id || ',' || sent_id || ']'))[1:" + str(num_pps) + "]  "+"FROM "+self.arg['relation_table']+" WHERE type_a_"+type_a['name']+"@>'"\
		+type_a['type']+"' AND type_b_"+type_b['name']+"@>'"+ type_b['type']+"' AND relation_type='"+relation_type + "' GROUP BY entity_a,entity_b) x ORDER BY RANDOM() LIMIT " +str(num_edges)
		q = self.db.query(query_string)
		result={'node_a': {}, 'node_b': {}, 'edges': []}
		for p in list(self.generate_random_walks(q.dictresult())):
			result['node_a'][p[0]]=[]
			result['node_b'][p[1]]=[]
			result['edges'].append({'source':p[0], 'target':p[1]})
		#print result
		return result

	def query_links(self, type_a, type_b, relation_type, num_edges=5, num_pps=1):
		#type_a={'mesh':0, 'name':"Chemicals_and_Drugs"}
		try:
			type_a = ast.literal_eval(type_a)
			type_b = ast.literal_eval(type_b)
		except:
			pass

		self.db.query("set statement_timeout TO 0")
		#query_string = "SELECT * INTO " +self.identity+ " FROM (SELECT DISTINCT ON(entity_a,entity_b) entity_a,entity_b,sent_id  "+"FROM "+self.arg['relation_table']+" WHERE type_a_"+type_a['name']+"@>'"\
		#+type_a['type']+"' AND type_b_"+type_b['name']+"@>'"+ type_b['type']+"' AND relation_type='"+relation_type + "') x ORDER BY RANDOM() LIMIT " +str(num_edges)
		query_string_v2 = "SELECT * FROM (SELECT entity_a,entity_b,(array_agg('[' || article_id || ',' || sent_id || ']'))[1:" + str(num_pps+2) + "] as sents  "+"FROM "+self.arg['relation_table']+" WHERE type_a_"+type_a['name']+"@>'"\
		+type_a['type']+"' AND type_b_"+type_b['name']+"@>'"+ type_b['type']+"' AND relation_type='"+relation_type + "' GROUP BY entity_a,entity_b) x ORDER BY RANDOM() LIMIT " +str(num_edges)
		q = self.db.query(query_string_v2)
		result = q.dictresult()
		query_a = []
		query_b = []
		query_edges = []
		for r in result:
			query_a.append(r['entity_a'])
			query_b.append(r['entity_b'])
			article = dict()
			for x in r['sents']:
				x = ast.literal_eval(x)
				article[x[0]]=str(x[1])
			query_edges.append({'source':r['entity_a'], 'target':r['entity_b'], 'sids':article.values(), 'sents':[]})

		red_node = dict()
		for v in query_a:
			#print "select distinct on (article_id) article_title, pmid, sent from entity_table where entity_name= '" + v['entity_a'] + "' LIMIT "+str(num_pps)
			#print "select distinct on (article_id) article_title, pmid, sent from entity_table where entity_name= '" + v['entity_a'] + "' LIMIT 2" 
			tmp=self.db.query("select article_title, pmid, sent from entity_table where entity_name= '" + v + "' LIMIT "+str(num_pps))
			#tmp=self.db.query("select distinct on (article_id) article_title, pmid, sent from entity_table where entity_name= '" + v['entity_a'] + "' LIMIT "+str(num_pps))
			red_node[v] = map(lambda x:(x['article_title'],x['sent'],x['pmid']),tmp.dictresult())
		#query_b=self.db.query("select entity_b from "+self.identity)
		blue_node = dict()
		for v in query_b:
			#pass
			#print "select distinct on (article_id) article_title, pmid, sent from entity_table where entity_name= '" + v['entity_b'] + "' LIMIT "+str(num_pps)
			tmp=self.db.query("select article_title, pmid, sent from entity_table where entity_name= '" + v + "' LIMIT "+str(num_pps))
			#tmp=self.db.query("select distinct on (article_id) article_title, pmid, sent from entity_table where entity_name= '" + v['entity_b'] + "' LIMIT "+str(num_pps))
			blue_node[v] = map(lambda x:(x['article_title'],x['sent'],x['pmid']),tmp.dictresult())
		#print red_node,blue_node
		for edge in query_edges:
			for s_id in edge['sids'][:num_pps]:
				tmp = self.db.query("select article_title, pmid, sent from entity_table where sent_id= '" + s_id + "' LIMIT 1")
				edge['sents'].append(tmp.dictresult()[0])
		#query_edge = "SELECT DISTINCT T.entity_a as source, T.entity_b as target, E.pmid, E.article_title,E.sent FROM " + self.arg['entity_table'] + " AS E INNER JOIN "+\
		#self.identity+" T ON E.sent_id = T.sent_id";
		#query_edges = "SELECT distinct on (R.article_id) R.article_id, R.sent_id from " + self.arg['relation_table']+ " AS R inner join " + self.identity+  \
		#" T on R.entity_a = T.entity_a and R.entity_b = T.entity_b and R.relation_type = \'" + relation_type +"' LIMIT " +str(num_pps)
		#"distinct on (article_id) inner join on entity_a, entity_b, relation_type"
		#q = self.db.query(query_edge)
		#self.db.query("drop table "+self.identity)
		return {'node_a':red_node,'node_b':blue_node,'edge':query_edges}

#class db_utils(object)
if __name__ == '__main__':
	# sys.argv[1] = "./data/sample_data.json"
	# sys.argv[2] = "entity_table"
	# sys.argv[2] = "relation_table"
	# sys.argv[3] = "./data/final_pmid_dict.m"

	#print(sys.argv)
	#t
	if sys.argv[1] == 'query':
		if sys.argv[2] == 'network':
			tmp_utils = data_utils({'entity_table': sys.argv[3], 'relation_table': sys.argv[4]})
			result = tmp_utils.query_links(type_a=sys.argv[5], type_b=sys.argv[6], relation_type=sys.argv[7], num_edges=sys.argv[8], num_pps=int(sys.argv[9]))
			print result
		elif sys.argv[2] == 'connected_network':
			tmp_utils = data_utils({'entity_table': sys.argv[3], 'relation_table': sys.argv[4]})
			result = tmp_utils.query_links_with_walk(type_a=sys.argv[5], type_b=sys.argv[6], relation_type=sys.argv[7], num_edges=sys.argv[8], num_pps=int(sys.argv[9]))
		elif sys.argv[2] == 'predict':
			tmp_utils = data_utils({'prediction_table': sys.argv[3]})
			result = tmp_utils.query_prediction_v2(name_a=sys.argv[4], name_b=sys.argv[5], relation_type=sys.argv[6])
			print result
		elif sys.argv[2] == 'caseolap':
			tmp_utils = data_utils({'caseolap_table': sys.argv[3]})
			result = tmp_utils.query_distinctive_v2(target_type=sys.argv[4],
				output_types=sys.argv[5],relation_type=sys.argv[6],sub_types=sys.argv[7])
			print result
			
	else:
		if len(sys.argv) == 5:
			tmp_utils = data_utils({'data_file': sys.argv[1], 'entity_table': sys.argv[2], 'relation_table': sys.argv[3],'corpus_map': sys.argv[4]})
			tmp_utils.load_pmids()
			tmp_utils.insert_record()
		elif len(sys.argv) == 3:
			tmp_utils = data_utils({'data_file': sys.argv[1], 'query_table': sys.argv[2]})
			tmp_utils.insert_query()
			#tmp_utils = data_utils({'data_file': sys.argv[1], 'prediction_table': sys.argv[2]})
			#tmp_utils.insert_prediction()
		elif len(sys.argv) == 4:
			tmp_utils = data_utils({'data_file': sys.argv[1], 'caseolap_table': sys.argv[2]})
			#52
			for i in xrange(int(sys.argv[-1])):
				print "process file:",i
				tmp_utils.insert_caseolap(i)
	#tmp_utils.insert_relation()
	
	#sys.argv[1] = "relation_table"
	#sys.argv[2] = "{'name':'mesh', 'name':'Chemicals_and_Drugs'}"
	#sys.argv[3] = "{'name':'mesh', 'name':'Chemicals_and_Drugs'}"
	#sys.argv[4] = "isa"
	#tmp_utils = data_utils({'table_name': sys.argv[1]})
	#tmp_utils.query_links(type_a=sys.argv[2], type_b=sys.argv[3], relation_type=sys.argv[4])
	
	# '''
	# lines = open(sys.argv[1]).readlines()
	# print "lines", len(lines)
	# numthreads = 20
	# numlines = 10000
	# pool = multiprocessing.Pool(processes=numthreads)
	# result_list = pool.map(worker, (lines[line:line+numlines] for line in xrange(0,len(lines),numlines) ))
	# '''

	'''
	[{}, {}, {}]
	in each dict:
		a_id: the articleID of document that contains the entity a
		b_id: the articleID of document that contains the entity b
		entity_a: entity name
		entity_b: entity name 
	'''

