"""
Simulator of NB-IoT cell at the MAC level.
In this simulator :
    - Slotted Aloha contention
    - 3 M/D/1-PS queues
    - Impatience
    - Ghost messages suppression
    - User Plane optimization
"""

from enum import Enum
import math
import random
import time

# General Conf
id_max = 1000000
debug_ = False
single_tone = True
#NPRACH
rep_ra = None #[1,2,4,8,16,32,64,128] defined in run_simu
nprach_sc = 12 #RAO
backoff_ms = [0, 256, 512, 1024, 2048, 4096,8192,16384,32768,65536,131072,262144,524288, 524288, 524288, 524288]
#NPDCCH
nb_CCE_subframe = 2
npdcch_window = 64


#G is computed thanks to the infos in the configuration (number of RU per seconds)

#Communications

""" conf immuable """
preamble_duration_ms = 6.4
total_nprach_sc = 48
ratio_npbch_npss_nsss = 2.5/10
epsilon_lambda_t = 0.1
RU_max_UL = 10


class typeEvt(Enum):
    ARRIVAL = 0
    DEPARTURE = 1
    IMPATIENCE = 2
    ARRIVAL_COM = 3
    RAO = 4
class channel(Enum):
    NPDCCH = 0
    NPDSCH = 1
    NPUSCH = 2
    NPRACH = 3
class evt:
    def __init__(self, type_, date_, com_, queue_):
        super().__init__()
        self.type_ = type_
        self.date_ = date_
        self.com_ = com_
        self.queue_ = queue_

class communication:
    def __init__(self, id_, D_service_time):
        super().__init__()
        self.id_ = id_
        self.rate_ = 0
        self.D_service_time = D_service_time  #depends on link budget 
        self.nb_attempts = 0
    def rateModifier(self,t):
        self.rate_ += t
    def nvlleTentative(self):
        self.nb_attempts += 1
        

def removeEvt(evts, type_, id_, fil):

    for i in range(len(evts)):
        if(evts[i].type_ == type_ and evts[i].com_.id_ == id_ and evts[i].queue_ == fil):
            del evts[i]
            return 0
    #debug
    if(type_ == typeEvt.DEPARTURE):
        #No problem, the impatience was triggered when the communication had not even begun to be served yet.
        pass
    elif(type_ == typeEvt.IMPATIENCE):
        #print("Error. There is no event associated to this id_ and the type IMPATIENCE in the queue n° " + str(fil))
        #No problem, since a communication may have been served before the impatience in another queue arises.
        pass

def changeId(evts, type_, id_, id_new):
    for evt in evts:
        if(evt.type_ == type_ and evt.com_.id_ == id_):
            evt.com_.id_ = id_new
            return 0
    #debug
    print("Error. We tried to change the id of in an evt but can't find the event")
    
def ComputationNvxTaux(communications,simu_time, next_evt):
    queue_DEPARTURE = None
    com_DEPARTURE = None
    time_DEPARTURE = None
    #LOOKING FOR A POSSIBLE DEPARTURE
    i = 0
    for fil in communications:
        len_fil = len(fil)
        tx = 0
        if(len_fil>0):
            filet = 0
            for c in fil:
                tx = c.D_service_time/len_fil
                percentage_addition = ((next_evt.date_ - simu_time) * tx)
                if(filet == 2):
                    #print("Computation pourcentage " + str(c.D_service_time) + "    "+ str(next_evt.date_))
                    #print("ajout pourcentage : " + str(round(percentage_addition,2)))
                    pass
                #Test if the oldest communication will be finished before the next event.
                if(c.rate_ + percentage_addition >= 1):#if percentage addition = 0 it means that we are at the same time and therefore that we already had a rate at 1, with a DEPARTURE already recorded
                    DEPARTURE_time = simu_time + (1-c.rate_)/tx
                    if(time_DEPARTURE == None or time_DEPARTURE > DEPARTURE_time):
                        queue_DEPARTURE = i
                        com_DEPARTURE = c
                        time_DEPARTURE = DEPARTURE_time
                filet += 1
        i += 1

    #WHETHER OR NOT TO SCHEDULE THE NEXT DEPARTURE
    if(queue_DEPARTURE != None): #A DEPARTURE is to be planned before the next event
        for f in communications:
            len_fil = len(f)
            tx = 0
            for c in f:
                tx = c.D_service_time/len_fil
                percentage_addition = (time_DEPARTURE - simu_time) * tx #different progress because next evt to change
                c.rateModifier(percentage_addition)
        return evt(typeEvt.DEPARTURE, time_DEPARTURE, com_DEPARTURE, queue_DEPARTURE)
    else:
        for f in communications:
            for c in f:
                percentage_addition = (next_evt.date_ - simu_time) * tx #different progress because next evt to change
                c.rateModifier(percentage_addition)
        return None

def nextEvenement(evenements, fil):
    for evt in evenements:
        if evt.queue_ == fil:
            return evt
    return None

def addEvt(evts, evt):
    if(len(evts) == 0):
        evts.append(evt)
        return 0
    else:
        for i in range(len(evts)):
            if(evts[i].date_ > evt.date_):
                evts.insert(i, evt)
                return 0
        evts.append(evt) #If the date_ of the event is greater than all the others then it is added at the end.
        return 0

def simulation_slotted_aloha(coms):
    successful_coms = []
    unsuccessful_coms = []
    chosen_preamble = []
    for i in range(nprach_sc): #We create an empty list
        chosen_preamble.append([])
    for c in coms:
        p = random.randint(0,nprach_sc-1)
        chosen_preamble[p].append(c)
    for i in range(nprach_sc):
        if (len(chosen_preamble[i]) == 1):
            successful_coms.append(chosen_preamble[i][0])
        else:
            for c in chosen_preamble[i]:
                unsuccessful_coms.append(c)
    return successful_coms, unsuccessful_coms
def ComputationRALength():
    return math.ceil(preamble_duration_ms*rep_ra)/1000
def ComputationRscCom(payload_size_bits):
    c,ds,us = 0,0,0
    for i in rsc_NPDCCH:
        c += (i*rep_cc)
    c += (math.ceil(payload_size_bits/(link_budget_UL*RU_max_UL))*rep_cc)
    for i in rsc_NPDSCH:
        ds += (math.ceil(i/link_budget_DL)*rep_ds)
    for i in rsc_NPUSCH:
        us += (math.ceil(i/link_budget_UL)*rep_us)
    us += (math.ceil(payload_size_bits/link_budget_UL)*rep_us)
    return c, ds, us

def ComputationRuNpusch():
    """
    We consider RU of 24 RE so multitone.
    It is the factor 1000 of the DEPARTURE which considers that there are 1000 RU per second.
    return the number of RU per second in the NPUSCH (mu_npusch)
    """
    ratio_npusch = 1-(math.ceil(preamble_duration_ms*rep_ra)/nprach_period_ms)*(nprach_sc/total_nprach_sc)
    nb_RU_sec = 1000
    if(single_tone): nb_RU_sec = 1500
    return ratio_npusch * nb_RU_sec

def ComputationRuNpdsch():
    """
    return the number of RU per second in the NPDSCH (mu_npdsch)
    """
    ratio_shared = 1-ratio_npbch_npss_nsss
    ru_frame = 10*ratio_shared*(1-1/npdcch_period)
    return 100*ru_frame

def ComputationCceNpdcch():
    """
    return the mean number of CCE (control channel element) per second (mu_npdcch)
    """
    return 1000*(1-ratio_npbch_npss_nsss)*nb_CCE_subframe/npdcch_period
def simu():
    # Initialisation
    evenements = []
    simu_time = 0
    gen_id = 0
    c_in_queue = [[], [], []]
    com_for_RA = []
    success = 0
    failure_tot = 0
    failures = [0,0,0]
    failure_rach = 0
    nb_total_clients = 0
    total_impatience = 0
    # First Com
    first_iat = random.expovariate(lambd)
    c = communication(gen_id, None) #None because not yet in a queue (different D's)
    evenements.append(evt(typeEvt.ARRIVAL_COM, simu_time + first_iat, c, None))#The arrival is common to the three queues and the size of the communication is not yet fixed.
    gen_id = (gen_id + 1 ) % id_max
    # First NPRACH opportunity
    addEvt(evenements, evt(typeEvt.RAO, simu_time + nprach_period_ms/1000, None, None))

    tempsRA = ComputationRALength()
    CCEs, RU_DL, RU_UL = ComputationRscCom(payload_size_bits)
    D_npdcch, D_npdsch, D_npusch = ComputationCceNpdcch()/CCEs, ComputationRuNpdsch()/RU_DL, ComputationRuNpusch()/RU_UL
    T_NPDCCH, T_NPDSCH, T_NPUSCH = npdcch_window*rep_cc*npdcch_period/(0.75*1000) , 0.128/0.75, 0.064
    T_npdcch, T_npdsch, T_npusch = CCEs*T_NPDCCH, len(rsc_NPDSCH)*T_NPDSCH, len(rsc_NPUSCH)*T_NPUSCH + math.ceil(payload_size_bits/(link_budget_UL*RU_max_UL))*T_NPUSCH
    #print("SIMULATOR----------")
    #print(D_npdcch, D_npdsch, D_npusch)
    #print(CCEs, RU_DL, RU_UL)
    #print(T_npdcch, T_npdsch, T_npusch)
    #print(ComputationCceNpdcch(), ComputationRuNpdsch(), ComputationRuNpusch())
    size_RAO = 0
    nb_RAO  =0
    while(nb_total_clients <= nb_simu_clients):

        n_evt = evenements.pop(0) #pop the first item on the list instead of the last one
        simu_time = n_evt.date_
        queue_concerne = n_evt.queue_

        if(n_evt.type_ == typeEvt.ARRIVAL):
            c_in_queue[queue_concerne].append(n_evt.com_)
            if(evenements[0].date_ == simu_time): #No need to Computationate the new rates if the next event is simultaneous.
                pass
            else:
                res = ComputationNvxTaux(c_in_queue, simu_time, evenements[0])# The new rate is Computationated for all queues as events can have global impact.
                if(res != None): 
                    addEvt(evenements, res)
                else:
                    pass
            
        elif(n_evt.type_ == typeEvt.DEPARTURE):
            try:
                c_in_queue[queue_concerne].remove(n_evt.com_)
            except:
                pass
                

            removeEvt(evenements, typeEvt.IMPATIENCE, n_evt.com_.id_, queue_concerne)

            if(evenements[0].date_ == simu_time): #No need to Computationate the new rates if the next event is simultaneous.
                pass
            else:
                res = ComputationNvxTaux(c_in_queue, simu_time, evenements[0])# The new rate is Computationated for all queues as events can have global impact.
                if(res != None): 
                    addEvt(evenements, res)
                else:
                    pass

            success += 1

        elif(n_evt.type_ == typeEvt.IMPATIENCE):
            total_impatience += n_evt.com_.rate_
            id_remove = n_evt.com_.id_
            for i in range(3):
                #Remove evenements of the queues
                if(i != queue_concerne):
                    removeEvt(evenements, typeEvt.IMPATIENCE, id_remove, i)
                # No need to remove a DEPARTURE event since a DEPARTURE is not put in the stack until it is the next item processed.
                # Remove communications from the queues
                #num_remove = 0
                for c in c_in_queue[i]:
                    if(c.id_ == id_remove):
                        c_in_queue[i].remove(c)
                        break

            n_evt.com_.nvlleTentative()
            if(n_evt.com_.nb_attempts == max_attempts):
                failures[queue_concerne] += 1
                failure_tot += 1
            else:
                bo = random.randint(0, backoff_ms[indice_bo])/1000
                addEvt(evenements, evt(typeEvt.ARRIVAL_COM, simu_time + bo, n_evt.com_, None))


            if(evenements[0].date_ == simu_time): #No need to Computationate the new rates if the next event is simultaneous.
                pass
            else:
                res = ComputationNvxTaux(c_in_queue, simu_time, evenements[0])# The new rate is Computationated for all queues as events can have global impact.
                if(res != None): 
                    addEvt(evenements, res)
                else:
                    pass
            failures[queue_concerne] += 1
            

        elif(n_evt.type_ == typeEvt.ARRIVAL_COM): # this is where we draw the next iat
            com_for_RA.append(n_evt.com_)
            if(n_evt.com_.nb_attempts == 0): # It's a first communication, we've got to pull the next one with Exponential Law
                #program the arrival of the next communication
                next_iat = random.expovariate(lambd)
                c = communication(gen_id,None)
                addEvt(evenements, evt(typeEvt.ARRIVAL_COM, simu_time+next_iat, c, None))
                gen_id = (gen_id+1)%id_max
                nb_total_clients += 1

            res = ComputationNvxTaux(c_in_queue, simu_time, evenements[0])# The new rate is Computationated for all queues as events can have global impact.
            if(res != None): 
                addEvt(evenements, res)
            else:
                pass

        elif(n_evt.type_ == typeEvt.RAO):
            successful_com, unsuccessful_com = simulation_slotted_aloha(com_for_RA)
            for com in successful_com:
                #NPDCCH
                c_c = communication(com.id_,D_npdcch)
                addEvt(evenements, evt(typeEvt.ARRIVAL, simu_time + tempsRA, c_c, 0))
                addEvt(evenements, evt(typeEvt.IMPATIENCE, simu_time + tempsRA + T_npdcch, c_c, 0))
                #NPDSCH
                c_ds = communication(com.id_,D_npdsch)
                addEvt(evenements, evt(typeEvt.ARRIVAL, simu_time + tempsRA, c_ds, 1))
                addEvt(evenements, evt(typeEvt.IMPATIENCE, simu_time + tempsRA + T_npdsch, c_ds, 1))
                #NPDSCH
                c_us = communication(com.id_,D_npusch)
                addEvt(evenements, evt(typeEvt.ARRIVAL, simu_time + tempsRA, c_us, 2))
                addEvt(evenements, evt(typeEvt.IMPATIENCE, simu_time + tempsRA + T_npusch, c_us, 2))
            for com in unsuccessful_com:
                com.nvlleTentative()
                if(com.nb_attempts == max_attempts):
                    failure_rach += 1
                    failure_tot += 1
                    continue
                bo = random.randint(0, backoff_ms[indice_bo])/1000
                addEvt(evenements, evt(typeEvt.ARRIVAL_COM, simu_time + bo, com, None))
                failure_rach += 1
            com_for_RA = []
            #Schedule next RAO
            addEvt(evenements, evt(typeEvt.RAO, simu_time + nprach_period_ms/1000, None, None))

            size_RAO += len(successful_com)
            nb_RAO += 1

            res = ComputationNvxTaux(c_in_queue, simu_time, evenements[0])# The new rate is Computationated for all queues as events can have global impact.
            if(res != None): 
                addEvt(evenements, res)
            else:
                pass

            
        
        #Test : stopping the simu because congestion quota of failure reached
        if((failure_tot)/(nb_simu_clients) >= percent_stop_failure):
            #print("on break prématurément")
            #print("No. of customers who entered the system : " + str(nb_total_clients))
            break
        #DEBUG
        
        if(debug_ and queue_concerne != None and queue_concerne == 2):
            if(queue_concerne != None): print(str(n_evt.type_) + ", queue n° " + str(queue_concerne))
            else: print(str(n_evt.type_))
            if(n_evt.com_ != None):
                print(" with id " + str(n_evt.com_.id_))
            for i in range(c_in_queue):
                print("Nb file n°"+ str(i) + " : " + str(len(c_in_queue[i])))
            print("Temps Simu : " + str(simu_time))
            if(len(c_in_queue[2])>0):
                print("Taux du prochain communications : " + str(round(c_in_queue[2][0].rate_, 2)))
                pass
            print("---------------")
            time.sleep(0.1)
            if(n_evt.type_ == typeEvt.IMPATIENCE): time.sleep(10000)
            #print("Temps de réponse = " + str(temps_reponse_tot))
            pass
        #END DEBUG

    p_success = (nb_total_clients-failure_tot)/(nb_total_clients)

    moyenne_impatience = 0
    if(failure_tot>0):
        moyenne_impatience = total_impatience/failure_tot
    else:
        moyenne_impatience = 1
    if(debug_):
        print("Impatience moyenne = " + str(round(moyenne_impatience,3)))
        print("Taux de succès  = " + str(round(p_success,3)))
        for i in range(len(failures)):
            print("Echec file n°" + str(i)+ " = " + str(failures[i]))
    #print(p_success, failures, failure_rach)
    #print(simu_time)
    return p_success, failures, failure_rach
    

def run_simu(lambd_, bits_per_RU_UL, bits_per_RU_DL, repetitions, nb_client, payload_size_bits_, nb_attempts, indice_backoff, nprach_period_ms_, RAOs,G, UP_opt, percent_stop_failure_):
    global lambd
    global link_budget_UL
    global link_budget_DL
    global nb_simu_clients
    global payload_size_bits
    global percent_stop_failure
    global max_attempts
    global indice_bo
    global nprach_period_ms
    global nprach_sc
    global npdcch_period
    global rsc_NPDCCH
    global rsc_NPDSCH
    global rsc_NPUSCH
    global rep_ra, rep_cc, rep_us, rep_ds

    lambd = lambd_
    link_budget_UL = bits_per_RU_UL
    link_budget_DL = bits_per_RU_DL
    nb_simu_clients = nb_client
    payload_size_bits = payload_size_bits_
    percent_stop_failure = percent_stop_failure_
    max_attempts = nb_attempts
    indice_bo = indice_backoff
    nprach_period_ms = nprach_period_ms_
    nprach_sc = RAOs
    npdcch_period = G
    rep_ra, rep_cc, rep_us, rep_ds = repetitions[0], repetitions[1], repetitions[2], repetitions[3]
    if(UP_opt):
        rsc_NPDCCH = [1, 1, 1, 1] #in number of CCE
        rsc_NPDSCH = [56, 304, 66]
        rsc_NPUSCH = [59, 128]
    else:
        rsc_NPDCCH = [1, 1, 1, 1, 1, 1, 1, 1] #in number of CCE
        rsc_NPDSCH = [56, 304, 88, 944, 80]
        rsc_NPUSCH = [56, 160, 104, 80]

    return simu()

def main():
    results = run_simu(35, 100, 150, [4, 1, 2, 2], 10000, 800, 8, 3, 80, 24, 4, True, 1)
    print("--- Results ---")
    print("Success Rate : " + str(results[0]))
    print("Failures due to congestion on NPDCCH, NPDSCH and NPUSCH : " + str(results[1]))
    print("Failures due to collisions on NPRACH : " + str(results[2]))

main()




