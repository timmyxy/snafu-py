### What does this script do?
### 
### 1) Import the USF network from disk
### 2) Generate toy data (censored random walks) from that network for many pseudo-participants
### 3) Estimate the best network from the data using one or several methods, showing how the method
###    improves as more participants are added
### 4) Write data about those graphs to a CSV (cost, SDT measures)


import snafu
import networkx as nx
import numpy as np

# import the USF network and dictionary of items
usf_graph, usf_items = snafu.read_graph("./snet/USF_animal_subset.snet")

# convert network from adjacency matrix to networkx format
usf_graph_nx = nx.from_numpy_matrix(usf_graph)
usf_numnodes = len(usf_items)           # how many items are in the USF network

# parameters for simulating data from the USF network
numsubs = 1             # how many subjects?
numlists = 3            # how many lists per subject?
listlength = 35         # how many unique items should each list traverse?
numsims = 10            # how many simulations to perform?

#methods = ['rw','goni','chan','kenett','fe','uinvite_flat','uinvite_hierarchical']
methods=['uinvite_hierarchical']    # which methods to use for reconstructing network?

# describe what your data should look like
toydata=snafu.Data({
        'jump': 0.0,
        'jumptype': "stationary",
        'priming': 0.0,
        'jumponcensored': None,
        'censor_fault': 0.0,
        'emission_fault': 0.0,
        'startX': "stationary",     # stationary, uniform, or a specific node?
        'numx': numlists,           # number of lists per subject
        'trim': listlength })       # 

# some parameters of the fitting process
fitinfo=snafu.Fitinfo({
        'startGraph': "goni_valid",
        'record': False,
        'directed': False,
        'prior_method': "zeroinflatedbetabinomial",
        'zibb_p': 0.5,
        'prior_a': 2,
        'prior_b': 1,
        'goni_size': 2,
        'goni_threshold': 2,
        'followtype': "avg", 
        'prune_limit': np.inf,
        'triangle_limit': np.inf,
        'other_limit': np.inf })

# generate data for `numsub` participants, each having `numlists` lists of `listlengths` items
seednum=0

with open('usf_reconstruction_results.csv','w',0) as fh:
    fh.write("method,simnum,ssnum,hit,miss,falsealarms,correctrejections,cost,startseed\n")

    for simnum in range(numsims):
        data = []           # Xs using usf_item indices
        data_hier = []      # Xs using individual graph indices (nodes only generated by subject)
        numnodes = []       # number of unique nodes traversed by each participant
        items = []          # individual participant index-label dictionaries
        startseed = seednum # random seed

        for sub in range(numsubs):
            
            # generate lists for each participant
            Xs = snafu.genX(usf_graph_nx, toydata, seed=seednum)[0]
            data.append(Xs)

            # record number of unique nodes traversed by each participant's data
            itemset = set(snafu.flatten_list(Xs))
            numnodes.append(len(itemset))

            # translate Xs and item dictionaries to local space for each participant
            # used only for hierarchical model
            ss_Xs, ss_items = snafu.groupToIndividual(Xs, usf_items)
            items.append(ss_items)
            data_hier.append(ss_Xs)
            
            seednum += numlists         # increment random seed so we dont get the same lists next time

        for ssnum in range(1,len(data)+1):
            print simnum, ssnum
            flatdata = snafu.flatten_list(data[:ssnum])  # flatten list of lists as if they came from the same participant
            
            # Generate Naive Random Walk graph from data
            if 'rw' in methods:
                rw_graph = snafu.nrw(flatdata, usf_numnodes)

            # Generate Goni graph from data
            if 'goni' in methods:
                goni_graph = snafu.goni(flatdata, usf_numnodes, fitinfo=fitinfo)

            # Generate Chan graph from data
            if 'chan' in methods:
                chan_graph = snafu.chan(flatdata, usf_numnodes)
            
            # Generate Kenett graph from data
            if 'kenett' in methods:
                kenett_graph = snafu.kenett(flatdata, usf_numnodes)

            # Generate First Edge graph from data
            if 'fe' in methods:
                fe_graph = snafu.firstEdge(flatdata, usf_numnodes)
               
            # Generate non-hierarchical U-INVITE graph from data
            if 'uinvite_flat' in methods:
                uinvite_flat_graph, ll = snafu.uinvite(flatdata, toydata, usf_numnodes, fitinfo=fitinfo)
            
            # Generate hierarchical U-INVITE graph from data
            if 'uinvite_hierarchical' in methods:
                uinvite_graphs, priordict = snafu.hierarchicalUinvite(data_hier[:ssnum], items[:ssnum], numnodes[:ssnum], toydata, fitinfo=fitinfo)
                
                # U-INVITE paper uses an added "threshold" such that at least 2 participants must have an edge for it to be in the group network
                # So rather than using the same prior as the one used during fitting, we have to generate a new one
                priordict = snafu.genGraphPrior(uinvite_graphs, items[:ssnum], fitinfo=fitinfo, mincount=2)

                # Generate group graph from the prior
                uinvite_group_graph = snafu.priorToGraph(priordict, usf_items)

            # Write data to file!
            for method in methods:
                if method=="rw": costlist = [snafu.costSDT(rw_graph, usf_graph), snafu.cost(rw_graph, usf_graph)]
                if method=="goni": costlist = [snafu.costSDT(goni_graph, usf_graph), snafu.cost(goni_graph, usf_graph)]
                if method=="chan": costlist = [snafu.costSDT(chan_graph, usf_graph), snafu.cost(chan_graph, usf_graph)]
                if method=="kenett": costlist = [snafu.costSDT(kenett_graph, usf_graph), snafu.cost(kenett_graph, usf_graph)]
                if method=="fe": costlist = [snafu.costSDT(fe_graph, usf_graph), snafu.cost(fe_graph, usf_graph)]
                if method=="uinvite_flat": costlist = [snafu.costSDT(uinvite_flat_graph, usf_graph), snafu.cost(uinvite_flat_graph, usf_graph)]
                if method=="uinvite_hierarchical": costlist = [snafu.costSDT(uinvite_group_graph, usf_graph), snafu.cost(uinvite_group_graph, usf_graph)]
                costlist = snafu.flatten_list(costlist)
                fh.write(method + "," + str(simnum) + "," + str(ssnum))
                for i in costlist:
                    fh.write("," + str(i))
                fh.write("," + str(startseed))
                fh.write('\n')
