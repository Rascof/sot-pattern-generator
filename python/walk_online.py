import sys
import logging
from numpy import *
from dynamic_graph import plug
from dynamic_graph.sot.core import *
from dynamic_graph.sot.core.math_small_entities import Derivator_of_Matrix
from dynamic_graph.sot.dynamics import Dynamic
import dynamic_graph.script_shortcuts
from dynamic_graph.script_shortcuts import optionalparentheses
from dynamic_graph.matlab import matlab
from dynamic_graph.sot.core.meta_task_6d import MetaTask6d,toFlags
sys.path.append("/home/nddang/src/sotpy/sot-pattern-generator/python")
from robotSpecific import pkgDataRootDir,modelName,robotDimension,initialConfig,gearRatio,inertiaRotor

OPENHRP = True
if "solver" not in globals().keys():
    OPENHRP = False
    from dynamic_graph.sot.dynamics.tools import solver, robot

import time
robotName = 'hrp14small'

logger = logging.getLogger()
logging.basicConfig()
logger.setLevel(logging.DEBUG)
dt = 0.005
def totuple( a ):
    al=a.tolist()
    res=[]
    for i in range(a.shape[0]):
        res.append( tuple(al[i]) )
    return tuple(res)

# --- MAIN LOOP ------------------------------------------

qs=[]
try:
    import robotviewer
    clt = robotviewer.client()
    clt.Ping()
except:
    clt = None

def inc():
    robot.device.increment(dt)
    state = robot.device.state.value
    qs.append(state)
    if clt:
        clt.updateElementConfig('hrp', list(state) + 10*[0])

from ThreadInterruptibleLoop import *

delta_time = 0
nb_step_modified = 0
test_change_foot = True

def generate_event():
    global delta_time, nb_step_modified, test_changed_foot
    stopping_time = 70*200
    if t > stopping_time:
        pass

@loopInThread
def loop():
    inc()
#    generate_event()

runner=loop()

@optionalparentheses
def go():
    runner.play()

@optionalparentheses
def stop(): runner.pause()
@optionalparentheses
def next(): inc() #runner.once()

# --- shortcuts -------------------------------------------------
@optionalparentheses
def n():
    inc()
    qdot()
@optionalparentheses
def n5():
    for loopIdx in range(5): inc()
@optionalparentheses
def n10():
    for loopIdx in range(10): inc()
@optionalparentheses
def q():
    if 'dyn' in globals(): print robot.dynamic.ffposition.__repr__()
    print robot.device.state.__repr__()
@optionalparentheses
def qdot(): print robot.device.control.__repr__()
@optionalparentheses
def t(): print robot.device.state.time-1
@optionalparentheses
def iter():         print 'iter = ',robot.device.state.time
@optionalparentheses
def status():       print runner.isPlay

# --- PG ---------------------------------------------------------
from dynamic_graph.sot.pattern_generator import PatternGenerator,Selector
modelDir = pkgDataRootDir[robotName]
xmlDir = pkgDataRootDir[robotName]
specificitiesPath = xmlDir + '/HRP2SpecificitiesSmall.xml'
jointRankPath = xmlDir + '/HRP2LinkJointRankSmall.xml'
robotDim = robotDimension[robotName]
pg = PatternGenerator('pg')
pg.setVrmlDir(modelDir+'/')
pg.setVrml(modelName[robotName])
pg.setXmlSpec(specificitiesPath)
pg.setXmlRank(jointRankPath)
pg.buildModel()

# Standard initialization
pg.parseCmd(":samplingperiod 0.005")
pg.parseCmd(":previewcontroltime 1.6")
pg.parseCmd(":comheight 0.814")
pg.parseCmd(":omega 0.0")
pg.parseCmd(":stepheight 0.05")
pg.parseCmd(":singlesupporttime 0.780")
pg.parseCmd(":doublesupporttime 0.020")
pg.parseCmd(":armparameters 0.5")
pg.parseCmd(":LimitsFeasibility 0.0")
pg.parseCmd(":ZMPShiftParameters 0.015 0.015 0.015 0.015")
pg.parseCmd(":TimeDistributeParameters 2.0 3.5 1.0 3.0")
pg.parseCmd(":UpperBodyMotionParameters 0.0 -0.5 0.0")
pg.parseCmd(":comheight 0.814")
pg.parseCmd(":SetAlgoForZmpTrajectory Morisawa")
# ONLINEWALKING SPECIFIC SETUP
pg.parseCmd(":onlinechangsstepframe relative")
pg.parseCmd(":SetAutoFirstStep false")

plug(robot.dynamic.position,pg.position)
plug(robot.dynamic.com,pg.com)
plug(robot.dynamic.signal('left-ankle'), pg.leftfootcurrentpos)
plug(robot.dynamic.signal('right-ankle'), pg.rightfootcurrentpos)
pg.motorcontrol.value = robotDim*(0,)
pg.zmppreviouscontroller.value = (0,0,0)
pg.initState()

# --- PG INIT FRAMES ---
geom = Dynamic("geom")
geom.setFiles(modelDir, modelName[robotName],specificitiesPath,jointRankPath)
geom.parse()
geom.createOpPoint('rf','right-ankle')
geom.createOpPoint('lf','left-ankle')
plug(robot.dynamic.position,geom.position)
geom.ffposition.value = 6*(0,)
geom.velocity.value = robotDim*(0,)
geom.acceleration.value = robotDim*(0,)

# --- Selector of Com Ref: when pg is stopped, pg.inprocess becomes 0
comRef = Selector('comRef'
                    ,['vector','ref',robot.dynamic.com,pg.comref])
plug(pg.inprocess,comRef.selec)

selecSupportFoot = Selector('selecSupportFoot'
                              ,['matrixHomo','pg_H_sf',pg.rightfootref,pg.leftfootref]
                              ,['matrixHomo','wa_H_sf',geom.rf,geom.lf]
                              )
plug(pg.SupportFoot,selecSupportFoot.selec)
sf_H_wa = Inverse_of_matrixHomo('sf_H_wa')
plug(selecSupportFoot.wa_H_sf,sf_H_wa.sin)
pg_H_wa = Multiply_of_matrixHomo('pg_H_wa')
plug(selecSupportFoot.pg_H_sf,pg_H_wa.sin1)
plug(sf_H_wa.sout,pg_H_wa.sin2)

# --- Compute the ZMP ref in the Waist reference frame.
wa_H_pg = Inverse_of_matrixHomo('wa_H_pg')
plug(pg_H_wa.sout,wa_H_pg.sin)
wa_zmp = Multiply_matrixHomo_vector('wa_zmp')
plug(wa_H_pg.sout,wa_zmp.sin1)
plug(pg.zmpref,wa_zmp.sin2)

# Connect the ZMPref to OpenHRP in the world reference frame.
pg.parseCmd(':SetZMPFrame world')
plug(pg.zmpref, robot.device.zmp)

############################################
# JOYSTICK
from dynamic_graph.sot.pattern_generator.pg_manager import PGManager, StepQueue
from dynamic_graph.sot.pattern_generator.step_time_line import TimeLine
from dynamic_graph.sot.pattern_generator.step_computer_joystick import StepComputerJoystick


stepqueue = StepQueue('stepqueue')
stepcomp = StepComputerJoystick('stepcomp')
steppg =  PGManager('steppg')
stepper = TimeLine('stepper')

stepper.setComputer('stepcomp')
stepper.setPGManager('steppg')
stepper.setQueue('stepqueue')

plug (pg.SupportFoot,stepcomp.contactfoot)
steppg.initPg('pg')
stepcomp.joystickin.value = (0,0,0)

robot.device.before.addSignal('stepper.trigger')
robot.device.before.addSignal('stepcomp.laststep')

# #time.sleep(0.5)
# time.sleep(0.5)

#pg.addStep(0,0.19,0)
#pg.addStep(0,-0.19,0)

# You can now modifiy the speed of the robot using set pg.velocitydes [3]( x, y, yaw)
#pg.velocitydes.value =(0.1,0.0,0.0)

# ---- TASKS -------------------------------------------------------------------

# ---- WAIST TASK ---
taskWaist=MetaTask6d('waist', robot.dynamic,'waist','waist')

# Build the reference waist pos homo-matrix from PG.
waistReferenceVector = Stack_of_vector('waistReferenceVector')
plug(pg.initwaistposref,waistReferenceVector.sin1)
plug(pg.initwaistattref,waistReferenceVector.sin2)
waistReferenceVector.selec1(0,3)
waistReferenceVector.selec2(0,3)
waistReference=PoseRollPitchYawToMatrixHomo('waistReference')
plug(waistReferenceVector.sout,waistReference.sin)
plug(waistReference.sout,taskWaist.featureDes.position)

taskWaist.feature.selec.value = '011100'
taskWaist.task.controlGain.value = 5

# --- TASK COM ---
featureCom = FeatureGeneric('featureCom')
plug(robot.dynamic.com,featureCom.errorIN)
plug(robot.dynamic.Jcom,featureCom.jacobianIN)
featureComDes = FeatureGeneric('featureComDes')
featureCom.sdes.value = 'featureComDes'
plug(comRef.ref,featureComDes.errorIN)
featureCom.selec.value = '011'

taskComPD = TaskPD('taskComPD')
taskComPD.add('featureCom')
plug(pg.dcomref,featureComDes.errordotIN)
plug(featureCom.errordot,taskComPD.errorDot)
taskComPD.controlGain.value = 40
taskComPD.setBeta(-1)


plug(pg.rightfootref,robot.features['right-ankle'].reference)
plug(pg.leftfootref,robot.features['left-ankle'].reference)

# ---- SOT ---------------------------------------------------------------------
#sot.control.unplug()
#sot = solver.sot
#sot.setNumberDofs(robotDim)
solver.sot.remove("robot_task_com")
solver.sot.remove("robot_task_left-ankle")
solver.sot.remove("robot_task_right-ankle")
solver.sot.push(taskWaist.task.name)
solver.sot.push("robot_task_left-ankle")
solver.sot.push("robot_task_right-ankle")
solver.sot.push(taskComPD.name)

robot.tasks['right-ankle'].controlGain.value = 180
robot.tasks['left-ankle'].controlGain.value = 180
if not OPENHRP:
    plug(solver.sot.control, robot.device.control)


# --- TRACER -----------------------------------------------------------------
from dynamic_graph.tracer import *
from dynamic_graph.tracer_real_time import *
tr = Tracer('tr')
tr.open('/tmp/','','.dat')
tr.start()
robot.device.after.addSignal('tr.triger')
robot.device.before.addSignal(robot.device.name + ".zmp")
tr.add("pg.zmpref",'pg.zmpref')
tr.add("pg.leftfootref",'pg.leftfootref')
tr.add("pg.rightfootref",'pg.rightfootref')
tr.add("pg.comref",'pg.comref')


if __name__ == '__main__':
    pg.parseCmd(":StartOnLineStepSequencing 0.0 -0.095 0.0 0.0 0.19 0.0 " 
                + " 0.2 -0.19 0.0 0.0 0.19 0.0 " 
                + " 0.2 -0.19 0.0 0.0 0.19 0.0 " 
                + " 0.2 -0.19 0.0 0.0 0.19 0.0 " 
                + " 0.2 -0.19 0.0 0.0 0.19 0.0 " 
                )
    #stepper.setState('start')
    while True:
        inc()
