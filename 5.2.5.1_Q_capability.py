# Import modules
import os
import sys

sys.path.append(r"""C:\Program Files (x86)\PTI\PSSE34\PSSBIN""")
os.environ['PATH'] = (r"C:\Program Files (x86)\PTI\PSSE34\PSSBIN;"+ os.environ['PATH'])
sys.path.append(r"""C:\Program Files (x86)\PTI\PSSE34\PSSPY27""")
os.environ['PATH'] = (r"C:\Program Files (x86)\PTI\PSSE34\PSSPY27;"+ os.environ['PATH'])
import psse34
import psspy
import redirect
import numpy
import math
import matplotlib as mpl
import matplotlib.pyplot as plt
import dyntools

# OPEN PSS
_i = psspy.getdefaultint()
_f = psspy.getdefaultreal()
_s = psspy.getdefaultchar()
redirect.psse2py()
psspy.psseinit(50000)

ierr = psspy.progress_output(6, ' ', [0, 0])  # disable output
ierr = psspy.prompt_output(6, ' ', [0, 0])  # disable output
ierr = psspy.report_output(6, ' ', [0, 0])  # disable output


# Set Simulation Path.
LoadScenario = "SimplifiedSystem"
ClauseName = "5.2.5.1_Q_capability"
ProgramPath = "C:/postDoc_work/GPS_TWSF/DYN/"
GridInfoPath = "C:/postDoc_work/GPS_TWSF/NEM/"
SMAModelPatrh = "C:/postDoc_work/GPS_TWSF/PSSE_models/SMASC_E158_SMAPPC_E127_PSSE/"
OutputFilePath = ProgramPath + "5.2.5.4_SimulationOutput_1.outx"
FigurePath = "C:/postDoc_work/GPS_TWSF/R_Results/"

if LoadScenario == "SummerPeakLoad":
    file_name = "--"
if LoadScenario == "WinterLowLoad":
    file_name = "---"
if LoadScenario == "SimplifiedSystem":
    file_name = "Tamworth_SMIB"

SMIB_bus_no=9999; # SIM bus number, where the generator is added for simplified SMIB system
POC_bus_gen=106; # POC bus number at near end/farm side
POC_bus_grid=9999; # POC bus number at far end/grid side
inverter_bus_1=100;
inverter_bus_2=200;

# Initialize
psspy.read(0, GridInfoPath + file_name + ".raw")

P_Record = []
Q_Record = []
T_Record = []
V_Record = []
S_Record = []

overloop = 0

S_1 = 83.6; # S for inverter bus.
S_BESS = 21.14; # S for inverter bus.

overloop=0; # add this line.
P_BESS_max=19;

Capacitor = 0;  # capacitor

for temperature in [25, 50]:
    for terminalv in [0.9, 1.0, 1.1]:
        if temperature == 50:
            derate = 0.909
        else:
            derate = 1.0

        psspy.plant_chng_3(SMIB_bus_no, 0,_i,[ terminalv,_f])  # the infinate bus number

        for P_Gen_1 in numpy.arange(0, S_1 * derate + 0.01, 2):
            psspy.read(0, GridInfoPath + file_name)
            psspy.plant_data_3(SMIB_bus_no, 0, _i, [terminalv, _f])
            # ierr = psspy.fdns([1, 0, 0, 1, 1, 0, 99, 0])
            P_BESS = P_Gen_1 / (S_1 * derate + 0.01) * P_BESS_max
            Q_Gen_1 = max(-9.26, -math.sqrt(S_1 * S_1 * derate * derate - P_Gen_1 * P_Gen_1))
            Q_Gen_BESS = max(-50.16, -math.sqrt(S_BESS * S_BESS * derate * derate - P_BESS * P_BESS))

            psspy.machine_chng_2(100, r"""1""", [_i, _i, _i, _i, _i, _i],  [P_Gen_1, Q_Gen_1, Q_Gen_1, Q_Gen_1, S_1, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])
            psspy.machine_chng_2(200, r"""1""", [_i, _i, _i, _i, _i, _i],   [P_BESS, Q_Gen_BESS, Q_Gen_BESS, Q_Gen_BESS, S_BESS, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])
            # psspy.machine_chng_2(200, r"""1""", [_i, _i, _i, _i, _i, _i],  [P_BESS, _f,   _f,    _f,    S_BESS, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])

            psspy.plant_data_3(SMIB_bus_no, 0, _i, [terminalv, _f])
            # fixed slope decoupled Newton-Raphson power flow calculation, 1_tap, 2_area_interchange, 3_phase_shift, 4_dc_tap, 5_switched shunt,6_flat_start, 7_Var_limit,8__non-divergent solution
            ierr = psspy.fdns([1, 0, 0, 1, 1, 0, 99, 0])

			#brnmsc: return real branch flow values
            ierr, pval = psspy.brnmsc(POC_bus_gen, POC_bus_grid, '1', 'P')  # POC_P_value

            ierr, qval = psspy.brnmsc(POC_bus_gen, POC_bus_grid, '1', 'Q')  # POC_Q_value

            ierr, vval = psspy.busdat(inverter_bus_1, 'PU')   				# inverter_terminal_voltage

            valid_pq = 0;
            loop = 0;
            while (1):
                if ((math.sqrt(P_Gen_1 ** 2 + Q_Gen_1 ** 2) < ((S_1 * min(derate, vval)) + 0.02)) and vval <= 1.15):
                    valid_pq = 1;
                    break;


                if loop >= 50:
                    valid_pq = 0;
                    overloop=overloop+1 # chang: add this line.
                    break;

                if ((math.sqrt(P_Gen_1 ** 2 + Q_Gen_1 ** 2) > ((S_1 * min(derate, vval)) + 0.02)) or vval > 1.15):
                    valid_pq = 0;
                    Q_Gen_1 = Q_Gen_1 + 1
                    psspy.machine_chng_2(100, r"""1""", [_i, _i, _i, _i, _i, _i],
                                         [P_Gen_1, Q_Gen_1, Q_Gen_1, Q_Gen_1, S_1, 0, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])
                    psspy.machine_chng_2(200, r"""1""", [_i, _i, _i, _i, _i, _i],
                                         [P_BESS, Q_Gen_BESS, Q_Gen_BESS, Q_Gen_BESS, S_BESS, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])
                    psspy.fdns([1, 0, 1, 1, 1, 1, 99, 0])

                    ierr, pval = psspy.brnmsc(POC_bus_gen, POC_bus_grid, '1', 'P')  # POC_P_value
                    ierr, qval = psspy.brnmsc(POC_bus_gen, POC_bus_grid, '1', 'Q')  # POC_Q_value
                    ierr, vval = psspy.busdat(inverter_bus_1, 'PU')  # inverter_terminal_voltage

                    loop = loop + 1;

            if valid_pq == 1:
                     P_Record.append(pval)
                     Q_Record.append(qval)
                     T_Record.append(temperature)
                     V_Record.append(terminalv)

        for P_Gen_1 in numpy.arange(0, S_1 * derate + 0.01, 2):     #################################CHANG: DO NOT CHANGE INDENTATION
            psspy.read(0, GridInfoPath + file_name)
            psspy.plant_data_3(SMIB_bus_no, 0, _i, [terminalv, _f])
            ierr = psspy.fdns([1, 0, 0, 1, 1, 0, 99, 0])
            P_BESS = P_Gen_1 / (S_1 * derate + 0.01) * P_BESS_max
            Q_Gen = min(50.16, math.sqrt(S_1 * S_1 * derate * derate - P_Gen_1 * P_Gen_1))
            Q_BESS = min(9.26, math.sqrt(S_BESS * S_BESS * derate * derate - P_BESS * P_BESS))
    #psspy.switched_shunt_chng_3(104, [_i, _i, _i, _i, _i, _i, _i, _i, _i, _i, _i, _i],
     #                           [_f, _f, _f, _f, _f, _f, _f, _f, _f, _f, Capacitor, _f], "")
    #psspy.switched_shunt_chng_3(204, [_i, _i, _i, _i, _i, _i, _i, _i, _i, _i, _i, _i],
    #                            [_f, _f, _f, _f, _f, _f, _f, _f, _f, _f, Capacitor, _f], "")
            psspy.machine_chng_2(100, r"""1""", [_i, _i, _i, _i, _i, _i],  [P_Gen_1, Q_Gen_1, Q_Gen_1, Q_Gen_1, S_1, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])
            psspy.machine_chng_2(200, r"""1""", [_i, _i, _i, _i, _i, _i],   [P_BESS, Q_BESS, Q_BESS, Q_BESS, S_BESS, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])
            # psspy.machine_chng_2(200, r"""1""", [_i, _i, _i, _i, _i, _i],  [P_BESS, _f,   _f,    _f,    S_BESS, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])
            psspy.plant_chng_3(SMIB_bus_no, 0, _i, [terminalv, _f])
            psspy.fdns([1, 0, 1, 1, 1, 1, 99, 0])
            ierr, pval = psspy.brnmsc(POC_bus_gen, POC_bus_grid, '1', 'P')  # POC_P_value
            ierr, qval = psspy.brnmsc(POC_bus_gen, POC_bus_grid, '1', 'Q')  # POC_Q_value
            ierr, vval = psspy.busdat(inverter_bus_1, 'PU')  # inverter_terminal_voltage
            valid_pq = 0;
            loop = 0;
            while (1):
                if math.sqrt(P_Gen_1 ** 2 + Q_Gen_1 ** 2) < ((S_1 * min(derate, vval)) + 0.02) and vval <= 1.15:
                    valid_pq = 1;
                    break;

                if loop >= 50:
                    valid_pq = 0;
                    overloop=overloop+1
                    break;

                if math.sqrt(P_Gen_1 ** 2 + Q_Gen_1 ** 2) > ((S_1 * min(derate, vval)) + 0.02) or vval > 1.15:
                    valid_pq = 0;
                    Q_Gen_1 = Q_Gen_1 - 1
                    psspy.machine_chng_2(100, r"""1""", [_i, _i, _i, _i, _i, _i],
                                                         [P_Gen_1, Q_Gen_1, Q_Gen_1, Q_Gen_1, S_1, 0, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])
                    psspy.machine_chng_2(200, r"""1""", [_i, _i, _i, _i, _i, _i],
                                         [P_BESS, Q_BESS, Q_BESS, Q_BESS, S_BESS, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f, _f])
                    psspy.fdns([1, 0, 1, 1, 1, 1, 99, 0])
                    ierr, pval = psspy.brnmsc(POC_bus_gen, POC_bus_grid, '1', 'P')  # POC_P_value
                    ierr, qval = psspy.brnmsc(POC_bus_gen, POC_bus_grid, '1', 'Q')  # POC_Q_value
                    ierr, vval = psspy.busdat(inverter_bus_1, 'PU')  # inverter_terminal_voltage
                    loop = loop + 1;
            if valid_pq == 1:
                P_Record.append(pval)
                Q_Record.append(qval)
                T_Record.append(temperature)
                V_Record.append(terminalv)

print overloop

P_Record = numpy.asarray(P_Record)
Q_Record = numpy.asarray(Q_Record)
T_Record = numpy.asarray(T_Record)
V_Record = numpy.asarray(V_Record)
numpy.savetxt('C:/postDoc_work/GPS_TWSF/R_Results/SolarFarmPQDiagram.csv', (P_Record, Q_Record, T_Record, V_Record), delimiter=',')

# Handling Data

DrawCenterX = 0;
DrawCenterY = -10;

##PQ_Array=[Q_Record-DrawCenterX,P_Record-DrawCenterY];
##PQ_Angle=numpy.arccos(numpy.divide(PQ_Array[0],numpy.sqrt(numpy.square(PQ_Array[0])+numpy.square(PQ_Array[1]))));


##P_Recrod=P_Record[SortIndex];
##Q_Record=Q_Record[SortIndex];
##T_Record=T_Record[SortIndex];
##V_Record=V_Record[SortIndex];


P_40_09 = P_Record[(T_Record == 25) & (V_Record == 0.9)];
P_40_10 = P_Record[(T_Record == 25) & (V_Record == 1.0)];
P_40_11 = P_Record[(T_Record == 25) & (V_Record == 1.1)];
P_50_09 = P_Record[(T_Record == 50) & (V_Record == 0.9)];
P_50_10 = P_Record[(T_Record == 50) & (V_Record == 1.0)];
P_50_11 = P_Record[(T_Record == 50) & (V_Record == 1.1)];

Q_40_09 = Q_Record[(T_Record == 25) & (V_Record == 0.9)];
Q_40_10 = Q_Record[(T_Record == 25) & (V_Record == 1.0)];
Q_40_11 = Q_Record[(T_Record == 25) & (V_Record == 1.1)];
Q_50_09 = Q_Record[(T_Record == 50) & (V_Record == 0.9)];
Q_50_10 = Q_Record[(T_Record == 50) & (V_Record == 1.0)];
Q_50_11 = Q_Record[(T_Record == 50) & (V_Record == 1.1)];

PQ_Array = [Q_40_09 - DrawCenterX, P_40_09 - DrawCenterY];
PQ_Angle = numpy.arccos(numpy.divide(PQ_Array[0], numpy.sqrt(numpy.square(PQ_Array[0]) + numpy.square(PQ_Array[1]))));
A_40_09_index = numpy.argsort(PQ_Angle / 121);  # MAY NEED TO CORRECT 150 TO 400.

PQ_Array = [Q_40_10 - DrawCenterX, P_40_10 - DrawCenterY];
PQ_Angle = numpy.arccos(numpy.divide(PQ_Array[0], numpy.sqrt(numpy.square(PQ_Array[0]) + numpy.square(PQ_Array[1]))));
A_40_10_index = numpy.argsort(PQ_Angle / 121); # MAY NEED TO CORRECT 150 TO 400.

PQ_Array = [Q_40_11 - DrawCenterX, P_40_11 - DrawCenterY];
PQ_Angle = numpy.arccos(numpy.divide(PQ_Array[0], numpy.sqrt(numpy.square(PQ_Array[0]) + numpy.square(PQ_Array[1]))));
A_40_11_index = numpy.argsort(PQ_Angle / 121);

PQ_Array = [Q_50_09 - DrawCenterX, P_50_09 - DrawCenterY];
PQ_Angle = numpy.arccos(numpy.divide(PQ_Array[0], numpy.sqrt(numpy.square(PQ_Array[0]) + numpy.square(PQ_Array[1]))));
A_50_09_index = numpy.argsort(PQ_Angle / 121);

PQ_Array = [Q_50_10 - DrawCenterX, P_50_10 - DrawCenterY];
PQ_Angle = numpy.arccos(numpy.divide(PQ_Array[0], numpy.sqrt(numpy.square(PQ_Array[0]) + numpy.square(PQ_Array[1]))));
A_50_10_index = numpy.argsort(PQ_Angle / 121.0);

PQ_Array = [Q_50_11 - DrawCenterX, P_50_11 - DrawCenterY];
PQ_Angle = numpy.arccos(numpy.divide(PQ_Array[0], numpy.sqrt(numpy.square(PQ_Array[0]) + numpy.square(PQ_Array[1]))));
A_50_11_index = numpy.argsort(PQ_Angle / 121.0);

P_40_09 = P_40_09[A_40_09_index];
P_40_10 = P_40_10[A_40_10_index];
P_40_11 = P_40_11[A_40_11_index];
P_50_09 = P_50_09[A_50_09_index];
P_50_10 = P_50_10[A_50_10_index];
P_50_11 = P_50_11[A_50_11_index];

Q_40_09 = Q_40_09[A_40_09_index];
Q_40_10 = Q_40_10[A_40_10_index];
Q_40_11 = Q_40_11[A_40_11_index];
Q_50_09 = Q_50_09[A_50_09_index];
Q_50_10 = Q_50_10[A_50_10_index];
Q_50_11 = Q_50_11[A_50_11_index];

# new folder if necessary
GraphPath = FigurePath + ClauseName + '/'
if not os.path.exists(GraphPath):
    os.makedirs(GraphPath)

# set figure preference
mpl.rcParams['grid.color'] = 'k'
mpl.rcParams['grid.linestyle'] = ':'
mpl.rcParams['grid.linewidth'] = 0.5
mpl.rcParams['axes.grid'] = 'on'
mpl.rcParams['font.size'] = 24
mpl.rcParams['lines.linewidth'] = 3.0
mpl.rcParams['legend.fancybox'] = True
mpl.rcParams['legend.loc'] = 'lower center'
mpl.rcParams['legend.numpoints'] = 3
mpl.rcParams['legend.fontsize'] = 'small'

CurrentFig, CurrentAx = plt.subplots(1, 1, sharex=False, figsize=(16, 12));

CurrentAx.plot(Q_40_09, P_40_09, color='blue', linestyle='-', marker='o', markevery=2);
CurrentAx.plot(Q_40_10, P_40_10, color='green', linestyle='-', marker='s', markevery=2);
CurrentAx.plot(Q_40_11, P_40_11, color='orange', linestyle='-', marker='^', markevery=2);
CurrentAx.plot([-25.67, -25.67, 25.67, 25.67], [0, 65, 65, 0], color='red', linestyle=':');
CurrentAx.legend([r"""T=25,V=0.9""", r"""T=25,V=1.0""", r"""T=25,V=1.1""", r"""Automatic Access Standard"""])
save_figure_name = GraphPath + 'P-Q Diagram @25 degree' + '.png'

# p_rate=96;
# q_low=-0.395*p_rate;
# q_up = 0.395*p_rate;
# CurrentAx.plot(Q_50_09,P_50_09,color='blue',linestyle='-',marker='o',markevery=5);
# CurrentAx.plot(Q_50_10,P_50_10,color='green',linestyle='-',marker='s',markevery=5);
# CurrentAx.plot(Q_50_11,P_50_11,color='orange',linestyle='-',marker='^',markevery=5);
# CurrentAx.plot([-40.29, -40.29, 40.29, 40.29], [0, 102, 102, 0],color='red',linestyle=':');
# CurrentAx.plot([q_low,q_low, q_up,q_up], [0, p_rate, p_rate, 0],color='BlueViolet',linestyle=':');
# CurrentAx.legend([r"""T=50,V=0.9""",r"""T=50,V=1.0""",r"""T=50,V=1.1""",r"""Automatic Access Standard""",r"""Proposed Access Standard"""])  #,r"""Proposed Minimum Reactive Power"""
# save_figure_name=GraphPath+'P-Q Diagram @50 degree'+'.png'


CurrentAx.tick_params(axis='both', which='both', labelsize=24)

##CurrentAx.set_xlim([-120,120])
##CurrentAx.set_ylim([ -10,140])

CurrentAx.set_xlabel(r"""Q / MVar""")
CurrentAx.set_ylabel(r"""P / MW  """)

CurrentFig.savefig(save_figure_name, format='png', dpi=150, bbox_inches='tight')
plt.close(CurrentFig)



