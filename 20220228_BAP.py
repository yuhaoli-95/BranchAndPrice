# -*- coding: utf-8 -*-
"""
Created on Mon Feb 28 22:32:57 2022

@author: WallrathR
"""


from pyscipopt import *
import numpy as np
import inspect
import matplotlib.pyplot as plt


def entering():
    return print("IN ", inspect.stack()[1][3])  # debugging magic


def leaving():
    return print("OUT ", inspect.stack()[1][3])  # debugging magic


class SameDiff(Conshdlr):
    def consdataCreate(self, name, item1, item2, constype, node):
        cons = self.model.createCons(self, name, stickingatnode=True)
        cons.data = {}
        cons.data["item1"] = item1
        cons.data["item2"] = item2
        cons.data["type"] = constype
        cons.data["npropagatedvars"] = 0
        cons.data["npropagations"] = 0
        cons.data["propagated"] = False
        cons.data["node"] = node
        return cons

    def checkVariable(self, cons, var, varid, nfixedvars):
        cutoff = False
        if var.getUbLocal() < 0.5:
            return nfixedvars, cutoff

        constype = cons.data["type"]
        packings = self.model.data["packings"]
        packingId = varid
        existitem1 = packings[packingId][cons.data["item1"]]
        existitem2 = packings[packingId][cons.data["item2"]]

        if (constype == "same" and (existitem1 != existitem2)) or (constype == "diff" and existitem1 and existitem2):
            infeasible, fixed = self.model.fixVar(var, 0.0)
            if infeasible:
                cutoff = True
            else:
                nfixedvars += 1
        return nfixedvars, cutoff

    def consdataFixVariables(self, cons, result):
        nfixedvars = 0
        cutoff = False
        v = cons.data["npropagatedvars"]
        while (v < len(self.model.data["var"])) and (not cutoff):
            nfixedvars, cutoff = self.checkVariable(
                cons, self.model.data["var"][v], v, nfixedvars)
            v += 1
        if cutoff:
            return {"result": SCIP_RESULT.CUTOFF}
        elif nfixedvars > 0:
            return {"result": SCIP_RESULT.REDUCEDDOM}
        else:
            return result

    def consactive(self, constraint):
        # entering()
        if constraint.data["npropagatedvars"] != len(self.model.data["var"]):
            constraint.data["propagated"] = False
            self.model.repropagateNode(constraint.data["node"])
        # leaving()

    def consdeactive(self, constraint):
        # entering()
        constraint.data["npropagatedvars"] = len(self.model.data["var"])
        # leaving()

    def conscheck(
        self,
        constraints,
        solution,
        checkintegrality,
        checklprows,
        printreason,
        completely,
    ):
        # for cons in constraints:
        #     item1 = cons.data["item1"]
        #     item2 = cons.data["item1"]
        #     packings = self.model.data["packings"]
        #     for i in range(len(self.model.data["var"])):
        #         sol = solution[self.model.data["var"][i]]
        #         if sol < 0.5:
        #             continue
        #         else:
        #             packingId = i
        #             existitem1 = packings[packingId][item1]
        #             existitem2 = packings[packingId][item2]
        #             if cons.data['type'] == 'same' and existitem1 != existitem2:
        #                 return {"result": SCIP_RESULT.INFEASIBLE}
        #             elif cons.data['type'] == 'diff' and existitem1 and existitem2:
        #                 return {"result": SCIP_RESULT.INFEASIBLE}

        return {"result": SCIP_RESULT.FEASIBLE}

    def consenfolp(self, constraints, nusefulconss, solinfeasible):
        pass

    def consenfops(self, constraints, nusefulconss, solinfeasible, objinfeasible):
        pass

    def consprop(self, constraints, nusefulconss, nmarkedconss, proptiming):
        result = {"result": SCIP_RESULT.DIDNOTFIND}
        for c in constraints:
            if not c.data["propagated"]:
                result = self.consdataFixVariables(c, result)
                c.data["npropagations"] += 1
                if result["result"] != SCIP_RESULT.CUTOFF:
                    c.data["propagated"] = True
                    c.data["npropagatedvars"] = len(self.model.data["var"])
                else:
                    leaving()
                    return {"result": SCIP_RESULT.CUTOFF}
        return result


class MyRyanFosterBranching(Branchrule):
    def __init__(self, model):
        self.model = model

    def branchexeclp(self, allowaddcons):
        lpcands, lpcandssol, lpcandsfrac, nlpcands, npriolpcands, nfracimplvars = self.model.getLPBranchCands()

        fractionalities = np.zeros(
            [len(self.model.data["widths"]), len(self.model.data["widths"])])

        for ii in range(len(lpcands)):

            solval = lpcandssol[ii]

            packingNum = self.model.data["varnames"].index(lpcands[ii].name)

            currentpacking = self.model.data["packings"][packingNum]

            con_id = np.where(np.array(currentpacking) == 1)[0]

            for i in con_id:
                for j in con_id:
                    if i == j:
                        continue
                    fractionalities[i, j] += solval

        temp = np.fmin(fractionalities, 1 - fractionalities)

        x_index, y_index = np.where(temp == np.max(temp))

        row1 = x_index[0]

        row2 = y_index[0]

        childsame = self.model.createChild(
            0.0, self.model.getLocalTransEstimate())

        childdiff = self.model.createChild(
            0.0, self.model.getLocalTransEstimate())

        conssame = self.model.data["conshdlr"].consdataCreate(
            "some_same_name", row1, row2, "same", childsame)

        consdiff = self.model.data["conshdlr"].consdataCreate(
            "some_diff_name", row1, row2, "diff", childdiff)

        self.model.addConsNode(childsame, conssame)

        self.model.addConsNode(childdiff, consdiff)

        self.model.data['branchingCons'].append(conssame)

        self.model.data['branchingCons'].append(consdiff)

        return {"result": SCIP_RESULT.BRANCHED}


class MyVarBranching(Branchrule):
    def __init__(self, model):
        self.model = model

    def branchexeclp(self, allowaddcons):

        (
            lpcands,
            lpcandssol,
            lpcandsfrac,
            nlpcands,
            npriolpcands,
            nfracimplvars,
        ) = self.model.getLPBranchCands()

        integral = lpcands[0]

        self.model.branchVar(integral)

        return {"result": SCIP_RESULT.BRANCHED}

# creates one pricing problem given the processing times matrix and the machine index


class Pricing:

    def __init__(self, initProcessingTimes, i, n):
        self.n = n
        self.s = {}
        self.f = {}
        self.x = {}
        self.processing_times = initProcessingTimes
        self.machineIndex = i
        self.bigM = 100
        self.pricing = None
        self.createPricing()

    def createPricing(self):

        # 2) CREATE PRICING

        self.pricing = Model("Pricing")
        # self.pricing.params.outputflag = 0
        # self.pricing.modelSense = GRB.MINIMIZE

        for j in range(0, self.n):
            self.s[j] = self.pricing.addVar(
                vtype="C", name="start(%s)" % (j), lb=0.0, ub=100.0)
            self.f[j] = self.pricing.addVar(
                vtype="C", name="finish(%s)" % (j), lb=0.0, ub=100.0)

        # Create order matrix
        for j in range(0, self.n):
            for k in range(0, self.n):
                self.x[j, k] = self.pricing.addVar(
                    vtype="B", name="x(%s,%s)" % (j, k))


        for j in range(0, self.n):
            self.pricing.addCons(self.s[j] + self.processing_times[j,
                                 self.machineIndex] == self.f[j], "startFinish(%s)" % (j))

        for j in range(0, self.n):
            for k in range(0, self.n):
                if k != j:
                    self.pricing.addCons(
                        self.x[j, k] + self.x[k, j] == 1, "precedence(%s)" % (j))
                    # if j => k, then start time of j should be 0
                    self.pricing.addCons(self.s[j] <= (
                        1-self.x[j, k])*50, "fixAtZero(%s)" % (j))

        for k in range(0, self.n):
            for j in range(0, self.n):
                # for each job k the finishing date one machine i has to be smaller than the starting date of the next job j, (1) if j follows k on i, (2) if job k was not the cutoff job (last job) on i
                self.pricing.addCons(
                    self.f[k] <= self.s[j] + self.bigM*(1-self.x[k, j]), "finishStart(%s)" % (k))


class Pricer(Pricer):
    def addBranchingDecisionConss(self, subMIP, binWidthVars):
        for cons in self.model.data['branchingCons']:
            if (not cons.isActive()):
                continue
            item1 = cons.data['item1']
            item2 = cons.data['item2']

            if cons.data['type'] == 'same':
                subMIP.addCons(binWidthVars[item1] - binWidthVars[item2] == 0)
            elif cons.data['type'] == 'diff':
                subMIP.addCons(binWidthVars[item1] + binWidthVars[item2] <= 1)

    def addFixedVarsConss(self, subMIP, binWidthVars):
        for ii in range(len(self.model.data["var"])):
            if self.model.data["var"][ii].getUbLocal() < 0.5:
                currentPacking = self.model.data["packings"][ii]
                subMIP.addCons(
                    quicksum(w * v for (w, v) in zip(currentPacking, binWidthVars)) <= np.sum(currentPacking) - 1)

    # The reduced cost function for the variable pricer
    def pricerredcost(self):



        # Retrieving the dual solutions
        dualSolutionsAlpha = []
        dualSolutionsBeta = []
        dualSolutionsGamma = []
        
        for i, c in enumerate(self.data["alphaCons"]):
            dualSolutionsAlpha.append(self.model.getDualsolLinear(c))
            # dualSolutions.append(self.model.getDualsolSetppc(c))
        for i, c in enumerate(self.data["betaCons"]):
            dualSolutionsBeta.append(self.model.getDualsolLinear(c))
        for i, c in enumerate(self.data["gammaCons"]):
            dualSolutionsGamma.append(self.model.getDualsolLinear(c))

        #################################################################
        #################################################################
        
        # create pricing list
        self.pricingList = createPricingList()  # a list of m pricing problems
        
    
        # ... and use them as weights completion time problem.
        nbrPricingOpt = 0
        for i in range(self.data["m"]):
            pricing = self.pricingList["pricing(%s)"%i]
            for j in range(self.data["n"]):
                pricing.s[j].obj = -dualSolutionsBeta[i*self.data["m"] + j]
                pricing.pricing.getVarByName("finish(%s)" %(j)).obj = -dualSolutionsGamma[i*self.data["m"] + j]
                
                
                print('pricing.pricing.getVarByName("start(%s)" ).obj: ' %(j), pricing.pricing.getVarByName("start(%s)" %(j)).obj)
                print('pricing.pricing.getVarByName("finish(%s)" ).obj: ' %(j), pricing.pricing.getVarByName("finish(%s)" %(j)).obj)
            
                # for k in range(0,n):
                #     pricing.pricing.getVarByName("x(%s,%s)"%(j,k)).obj = omega["JobOrderOnMachine(%s,%s,%s)"%(j,k,i)]
                #     print("pricing.getVarByName(x(%s,%s)).obj: " %(j,k), pricing.pricing.getVarByName("x(%s,%s)"%(j,k)).obj)
     
       

        # Variables for the subMIP
        for i in range(len(dualSolutions)):
            varNames.append(varBaseName + "_" + str(i))
            binWidthVars.append(subMIP.addVar(
                varNames[i], vtype="B", obj=-1.0 * dualSolutions[i]))

        # Adding the knapsack constraint
        subMIP.addCons(
            quicksum(w * v for (w, v) in zip(self.model.data["widths"], binWidthVars)) <= self.model.data["rollLength"])

        # Avoid to generate columns which are fixed to zero
        self.addFixedVarsConss(subMIP, binWidthVars)

        # Add branching decisions constraints to the sub SCIP
        self.addBranchingDecisionConss(subMIP, binWidthVars)

        # Solving the subMIP to generate the most negative reduced cost packing
        subMIP.optimize()

        objval = 1 + subMIP.getObjVal()

        #################################################################
        #################################################################

        # Adding the column to the master problem
        if objval < -1e-08:

            currentNumVar = len(self.model.data["var"])

            # Creating new var; must set pricedVar to True
            newVar = self.model.addVar(
                "NewPacking_" + str(currentNumVar), vtype="I", obj=1.0, pricedVar=True)

            self.model.data["varnames"].append(
                "NewPacking_" + str(currentNumVar))

            # Adding the new variable to the constraints of the master problem
            newPacking = []
            for i, c in enumerate(self.data["cons"]):
                coeff = round(subMIP.getVal(binWidthVars[i]))
                self.model.addConsCoeff(c, newVar, coeff)
                # self.model.addVarBasicSetcover(c, newVar)

                newPacking.append(coeff)

            self.model.data["packings"].append(newPacking)
            self.model.data["var"].append(newVar)

        return {"result": SCIP_RESULT.SUCCESS}
    
    # The initialisation function for the variable pricer to retrieve the transformed constraints of the problem
    def pricerinit(self):
        for i, c in enumerate(self.data["alphaCons"]):
            self.data["alphaCons"][i] = self.model.getTransformedCons(c)
        for i, c in enumerate(self.data["betaCons"]):
            self.data["betaCons"][i] = self.model.getTransformedCons(c)
        for i, c in enumerate(self.data["gammaCons"]):
            self.data["gammaCons"][i] = self.model.getTransformedCons(c)
        


def createPricingList():
    # PARAMS
    n = 2  # number of jobs
    m = 2  # number of machines
    # job 1 takes 7 hours on machine 1, and 1 hour on machine 2, job 2 takes 1 hour on machine 1, and 7 hours on machine 2
    processing_times = np.array([[7, 1], [1, 7]])
    pricingList = {}
    for i in range(0, m):
        pricing = Pricing(processing_times, i, n)
        pricingList["pricing(%s)" % i] = pricing

    return pricingList


def test_binpacking():

    master = Model()

    # master.setPresolve(SCIP_PARAMSETTING.OFF)

    master.setIntParam("presolving/maxrestarts", 0)

    master.setParam('limits/time', 30 * 60)

    master.setSeparating(SCIP_PARAMSETTING.OFF)

    # master.setHeuristics(SCIP_PARAMSETTING.OFF)

    master.setObjIntegral()

    pricer = Pricer(priority=5000000)
    master.includePricer(pricer, "BinPackingPricer", "Pricer")

    conshdlr = SameDiff()

    master.includeConshdlr(
        conshdlr,
        "SameDiff",
        "SameDiff Constraint Handler",
        chckpriority=2000000,
        propfreq=1,
    )

    # my_branchrule = MyRyanFosterBranching(s)

    my_branchrule = MyVarBranching(master)

    master.includeBranchrule(
        my_branchrule,
        "test branch",
        "test branching and probing and lp functions",
        priority=10000000,
        maxdepth=-1,
        maxbounddist=1,
    )

    # # item widths
    # widths = [
    #     42, 69, 67, 57, 93, 90, 38, 36, 45, 42, 33, 79, 27, 57, 44, 84, 86, 92, 46, 38, 85, 33, 82, 73, 49, 70, 59, 23,
    #     57, 72, 74, 69, 33, 42, 28, 46, 30, 64, 29, 74, 41, 49, 55, 98, 80, 32, 25, 38, 82, 30, 35, 39, 57, 84, 62, 50,
    #     55, 27, 30, 36, 20, 78, 47, 26, 45, 41, 58, 98, 91, 96, 73, 84, 37, 93, 91, 43, 73, 85, 81, 79, 71, 80, 76, 83,
    #     41, 78, 70, 23, 42, 87, 43, 84, 60, 55, 49, 78, 73, 62, 36, 44, 94, 69, 32, 96, 70, 84, 58, 78, 25, 80, 58, 66,
    #     83, 24, 98, 60, 42, 43, 43, 39
    # ]
    # # width demand
    # demand = [1] * 120

    # # roll length
    # rollLength = 150
    # assert len(widths) == len(demand)

    # PARAMS
    n = 2  # number of jobs
    m = 2  # number of machines
    # job 1 takes 7 hours on machine 1, and 1 hour on machine 2, job 2 takes 1 hour on machine 1, and 7 hours on machine 2
    processing_times = np.array([[7, 1], [1, 7]])

    # We start with only randomly generated patterns.
    # pattern 1 is[[0,7],[7,8]]. The structure is [[start time job 1, start time job 2,...],[compl time job 1, compl time job 2,...]]
    patterns = [list([[[0, 7], [7, 8]],[[0, 7], [7, 8]]]),
                list([[[10, 12], [11, 19]],[[10, 12], [11, 19]]])]

    # adding the initial variables
    flowShopVars = []
    varNames = []
    varBaseName = "Pattern"
    packings = []
    lamb = []
    offset = []
    s = []
    f = []
    alphaCons = []
    betaCons = []
    gammaCons = []

    # for i in range(len(widths)):
    #     varNames.append(varBaseName + "_" + str(i))
    #     flowshopVars.append(s.addVar(varNames[i], vtype="B", obj=1.0))

    # Create lambda variables for these patterns.
    for i in range(0, m):
        for l in range(len(patterns[i])):
            lamb.append(master.addVar(vtype="B"))  # is pattern p used on machine i
        offset.append(master.addVar(vtype="C")) 

        for j in range(0, n):
            s.append(master.addVar(vtype="C"))
            f.append(master.addVar(vtype="C"))

        alphaCons.append(master.addCons(quicksum(lamb[l + i*m] for l in range(len(patterns[i]))) - 1 == 0, "convexityOnMachine(%s)" % (i), separate=False, modifiable=True))  # only one pattern per machine

    # define makespan
    c_max = master.addVar(vtype="C", name="makespan", obj=1.0)

    for i in range(0, m):
        for j in range(0, n):
            betaCons.append(master.addCons(quicksum(patterns[i][l][0][j]*lamb[l + i*m] for l in range(len(patterns[i]))) +
                                                               offset[i] - s[j + i*m] == 0, separate=False, modifiable=True))  # starting time on machine i for job j is determined by the starting time of job j in the selected pattern p
            # completion time on machine i for job j is determined by the completion time of job j in the selected pattern p
            gammaCons.append(master.addCons(quicksum(patterns[i][l][1][j]*lamb[l + i*m] for l in range(len(patterns[i]))) + offset[i] - f[j + i*m] == 0, separate=False, modifiable=True))
        if i != m-1:
            for j in range(0, n):
                master.addCons(f[j + i*m] <= s[j + (i+1)*m],
                               "interMachine(%s,%s)" % (i, j))
        for j in range(0, n):
            master.addCons(s[j + i*m] + processing_times[j, i] == f[j + i*m],
                           "startFinish(%s,%s)" % (i, j))

    for j in range(0, n):
        master.addCons(c_max >= f[j + (m-1)*m], "makespanConstrMachine(%s)" % (j))

    pricer.data = {}
    pricer.data["alphaCons"] = alphaCons
    pricer.data["betaCons"] = betaCons
    pricer.data["gammaCons"] = gammaCons
    pricer.data["m"] = m
    pricer.data["n"] = n

    master.data = {}
    master.data["s"] = s
    master.data["f"] = f
    master.data["offset"] = offset
    master.data["lamb"] = lamb
    master.data["varnames"] = varNames
    master.data["alphaCons"] = alphaCons
    master.data["betaCons"] = betaCons
    master.data["gammaCons"] = gammaCons
    master.data["patterns"] = patterns
    master.data["conshdlr"] = conshdlr
    master.data['branchingCons'] = []

    master.optimize()

    # # print original data
    # printWidths = "\t".join(str(e) for e in widths)
    # print("\nInput Data")
    # print("==========")
    # print("Roll Length:", rollLength)
    # print("Widths:\t", printWidths)
    # print("Demand:\t", "\t".join(str(e) for e in demand))

    # # print solution
    # widthOutput = [0] * len(widths)
    # print("\nResult")
    # print("======")
    # print("\t\tSol Value", "\tWidths\t", printWidths)
    # for i in range(len(s.data["var"])):
    #     rollUsage = 0
    #     solValue = s.getVal(s.data["var"][i])
    #     if solValue > 0:
    #         outline = "Packing_" + str(i) + ":\t" + \
    #             str(solValue) + "\t\tCuts:\t "
    #         for j in range(len(widths)):
    #             rollUsage += s.data["packings"][i][j] * widths[j]
    #             widthOutput[j] += s.data["packings"][i][j] * solValue
    #             outline += str(s.data["packings"][i][j]) + "\t"
    #         outline += "Usage:" + str(rollUsage)
    #         print(outline)

    # print("\t\t\tTotal Output:\t", "\t".join(str(e) for e in widthOutput))

    # print(s.getObjVal())


# Draw a Gantt chart with the current master solution

    # x_array = restructureX(x,m,n) #input x dictionary from solved model, output x numpy array
    fig = plt.figure()
    M = ['red', 'blue', 'yellow', 'orange', 'green', 'moccasin', 'purple', 'pink', 'navajowhite', 'Thistle',
         'Magenta', 'SlateBlue', 'RoyalBlue', 'Aqua', 'floralwhite', 'ghostwhite', 'goldenrod', 'mediumslateblue',
         'navajowhite', 'navy', 'sandybrown']
    M_num = 0
    for i in range(m):
        for j in range(n):

            Start_time = master.getVal(master.data["s"][j + i*m])
            End_time = master.getVal(master.data["f"][j + i*m])

            # Job=np.nonzero(x_array[j,:,i] == 1 )[0][0] # for each machine and each job position, find the job that takes this position
            Job = j
            plt.barh(i, width=End_time - Start_time, height=0.8, left=Start_time,
                     color=M[Job], edgecolor='black')
            plt.text(x=Start_time + ((End_time - Start_time) / 2 - 0.25), y=i - 0.2,
                     s=Job+1, size=15, fontproperties='Times New Roman')
            M_num += 1
    plt.yticks(np.arange(M_num + 1), np.arange(1, M_num + 2),
               size=8, fontproperties='Times New Roman')
    plt.xticks(np.arange(0, master.getObjVal() + 1, 1.0),
               size=8, fontproperties='Times New Roman')
    plt.ylabel("machine", size=20, fontproperties='SimSun')
    plt.xlabel("time", size=20, fontproperties='SimSun')
    plt.tick_params(labelsize=20)
    plt.tick_params(direction='in')
    plt.show()


if __name__ == "__main__":
    test_binpacking()
