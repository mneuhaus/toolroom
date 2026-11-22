FeatureScript 3070;
import(path : "onshape/std/common.fs", version : "3070.0");

// Millimeters. Origin = old rod lower end, X at laser axis,
// Y=0 old carriage rear mounting face. +Y toward laser, +Z upward.
// Fusion world origin: (531.81811,34.27056,110.598).
OriginalX::import(path : "ba32090a2fb2f5ef1388a6a9", version : "f411a9d279243d5a0e23f6ba");
Retained::import(path : "ddce30e642d7d3fa62166966", version : "4a05e5393383d419bcaf2636");
Home::import(path : "d4b4368e1d121d2d690903c8", version : "7495e94ed7522f19e832a23b");
const REVS = { "base" : 16, "carriage" : 16, "clamp" : 16, "idler" : 5, "sensorArm" : 16, "sensorBracket" : 16, "home" : 16, "xCarrier" : 16, "jaw" : 16 };
function solid(context is Context,id is Id) returns Query
{ return qBodyType(qCreatedBy(id,EntityType.BODY),BodyType.SOLID); }
function rect(context is Context,id is Id,x0,y0,z0,x1,y1,z1) returns Query
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(vector(0,y0,0)*millimeter,vector(0,-1,0),vector(1,0,0))});
 skRectangle(sk,"r",{"firstCorner":vector(x0,z0)*millimeter,"secondCorner":vector(x1,z1)*millimeter});skSolve(sk);
 opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":vector(0,1,0),"endBound":BoundingType.BLIND,"endDepth":(y1-y0)*millimeter});
 opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});return solid(context,id);
}
function cyl(context is Context,id is Id,p is Vector,axis is Vector,r,h) returns Query
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(p*millimeter,axis)});
 skCircle(sk,"c",{"center":vector(0,0)*millimeter,"radius":r*millimeter});skSolve(sk);
 opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":axis,"endBound":BoundingType.BLIND,"endDepth":h*millimeter});
 opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});return solid(context,id);
}
function cut(context is Context,id is Id,target is Query,tool is Query)
{opBoolean(context,id,{"targets":target,"tools":tool,"operationType":BooleanOperationType.SUBTRACTION});}
function join(context is Context,id is Id,target is Query,tool is Query)
{opBoolean(context,id,{"tools":qUnion([target,tool]),"operationType":BooleanOperationType.UNION});}
function holeY(context is Context,id is Id,target is Query,x,z,r,y,h)
{cut(context,id+"cut",target,cyl(context,id,vector(x,y,z),vector(0,1,0),r,h));}
function nutY(context is Context,id is Id,target is Query,x,z,af,y,h)
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(vector(x,y,z)*millimeter,vector(0,-1,0),vector(1,0,0))});
 var radius=af/sqrt(3);
 for(var i=0;i<6;i+=1)skLineSegment(sk,"e"~i,{"start":vector(cos(i*60*degree),sin(i*60*degree))*radius*millimeter,"end":vector(cos((i+1)*60*degree),sin((i+1)*60*degree))*radius*millimeter});
 skSolve(sk);opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":vector(0,1,0),"endBound":BoundingType.BLIND,"endDepth":h*millimeter});cut(context,id+"cut",target,solid(context,id));opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
}
function nutX(context is Context,id is Id,target is Query,x,y,z)
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(vector(x,y,z)*millimeter,vector(1,0,0),vector(0,1,0))});
 for(var i=0;i<6;i+=1)skLineSegment(sk,"e"~i,{"start":vector(cos(i*60*degree),sin(i*60*degree))*5.7/sqrt(3)*millimeter,"end":vector(cos((i+1)*60*degree),sin((i+1)*60*degree))*5.7/sqrt(3)*millimeter});
 skSolve(sk);opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":vector(1,0,0),"endBound":BoundingType.BLIND,"endDepth":2.5*millimeter});cut(context,id+"cut",target,solid(context,id));opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
}
function namePart(context is Context,q is Query,n is string,c is Color)
{setProperty(context,{"entities":q,"propertyType":PropertyType.NAME,"value":n});setProperty(context,{"entities":q,"propertyType":PropertyType.APPEARANCE,"value":c});}
function roundY(context is Context,id is Id,q is Query,r)
{
 var es=[];
 for(var e in evaluateQuery(context,qGeometry(qOwnedByBody(q,EntityType.EDGE),GeometryType.LINE)))
 {var l=evLine(context,{"edge":e});if(abs(l.direction[1])>0.999)es=append(es,e);}
 if(size(es)>0)opFillet(context,id,{"entities":qUnion(es),"radius":r*millimeter});
}
function label(context is Context,id is Id,q is Query,text is string,x,y,z,w,dir)
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(vector(x,y,z)*millimeter,vector(0,-1,0),vector(1,0,0))});
 skText(sk,"text",{"text":text,"fontName":"OpenSans-Regular.ttf","firstCorner":vector(-w/2,-1.2)*millimeter,"secondCorner":vector(w/2,1.2)*millimeter});skSolve(sk);
 opExtrude(context,id,{"entities":qSketchRegion(id+"sk",true),"direction":vector(0,dir,0),"endBound":BoundingType.BLIND,"endDepth":0.3*millimeter});cut(context,id+"cut",q,solid(context,id));opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
}
function roundZ(context is Context,id is Id,q is Query,r)
{
 var es=[];
 for(var e in evaluateQuery(context,qGeometry(qOwnedByBody(q,EntityType.EDGE),GeometryType.LINE)))
 {var l=evLine(context,{"edge":e});if(abs(l.direction[2])>0.999)es=append(es,e);}
 if(size(es)>0)opFillet(context,id,{"entities":qUnion(es),"radius":r*millimeter});
}

// Product details are applied to explicit blank edges before holes and fits.
// Equal-offset chamfers: https://cad.onshape.com/FsDoc/library.html#opChamfer
function productCorners(context is Context,id is Id,q is Query,axis,r,selection is map)
{
 var es=[];
 for(var e in evaluateQuery(context,qGeometry(qOwnedByBody(q,EntityType.EDGE),GeometryType.LINE))){
  var l=evLine(context,{"edge":e});
  if(abs(l.direction[axis])<0.999)continue;
  if(selection.coordinate!=undefined && abs(l.origin[selection.coordinate]/millimeter-selection.value)>0.001)continue;
  es=append(es,e);
 }
 if(size(es)==0)throw regenError("No edges selected for product corner detail");
 opChamfer(context,id,{"entities":qUnion(es),"chamferType":ChamferType.EQUAL_OFFSETS,"width":r*millimeter,"tangentPropagation":false});
}
function productFaceEdge(context is Context,id is Id,q is Query,axis,position,r)
{
 var es=[];
 for(var e in evaluateQuery(context,qGeometry(qOwnedByBody(q,EntityType.EDGE),GeometryType.LINE))){
  var bb=evBox3d(context,{"topology":e,"tight":true});
  if(abs(bb.minCorner[axis]/millimeter-position)<0.001 && abs(bb.maxCorner[axis]/millimeter-position)<0.001)es=append(es,e);
 }
 if(size(es)==0)throw regenError("No edges selected for product face detail");
 opChamfer(context,id,{"entities":qUnion(es),"chamferType":ChamferType.EQUAL_OFFSETS,"width":r*millimeter,"tangentPropagation":false});
}
// One font and fixed size classes. The normal points out of the service face.
function productMark(context is Context,id is Id,q is Query,text is string,p is Vector,normal is Vector,textX is Vector,w,h)
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(p*millimeter,normal,textX)});
 skText(sk,"text",{"text":text,"fontName":"OpenSans-Bold.ttf","firstCorner":vector(-w/2,-h/2)*millimeter,"secondCorner":vector(w/2,h/2)*millimeter});skSolve(sk);
 opExtrude(context,id,{"entities":qSketchRegion(id+"sk",true),"direction":-normal,"endBound":BoundingType.BLIND,"endDepth":0.4*millimeter});
 cut(context,id+"cut",q,solid(context,id));opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
}
function productArrowY(context is Context,id is Id,q is Query,x,y,z,length,headWidth)
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(vector(x,y,z)*millimeter,vector(0,1,0),vector(-1,0,0))});
 var a=length/2;var hw=headWidth/2;
 var pts=[vector(0,a),vector(hw,a-2),vector(0.45,a-2),vector(0.45,-a+2),vector(hw,-a+2),vector(0,-a),vector(-hw,-a+2),vector(-0.45,-a+2),vector(-0.45,a-2),vector(-hw,a-2)];
 for(var i=0;i<size(pts);i+=1)skLineSegment(sk,"e"~i,{"start":pts[i]*millimeter,"end":pts[(i+1)%size(pts)]*millimeter});skSolve(sk);
 opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":vector(0,-1,0),"endBound":BoundingType.BLIND,"endDepth":0.4*millimeter});
 cut(context,id+"cut",q,solid(context,id));opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
}

const BELT_ADJUST = { (millimeter) : [0,3,6] } as LengthBoundSpec;
const PROBE_CLEARANCE = { (millimeter) : [2.3,3.3,4.3] } as LengthBoundSpec;
function gussetX(context is Context,id is Id,x,y,z) returns Query
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(vector(x,y,z)*millimeter,vector(1,0,0),vector(0,1,0))});
 var pts=[vector(0,0),vector(12,0),vector(0,26)];
 for(var i=0;i<3;i+=1)skLineSegment(sk,"e"~i,{"start":pts[i]*millimeter,"end":pts[(i+1)%3]*millimeter});
 skSolve(sk);opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":vector(1,0,0),"endBound":BoundingType.BLIND,"endDepth":3*millimeter});
 opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});return solid(context,id);
}
// Exact bottom contour from Marc's m3_hybrid_hole, source microversion 6ecd8fee1a6ee4064330d6ad.
const M3_HYBRID_ARCS = [[[1.9331711969931729,0.8202738098439961],[1.818653347947321,1.0500000000000007],[1.6769635558805325,1.264038461538462]],[[-1.6769635558805327,1.2640384615384619],[-1.818653347947321,1.050000000000001],[-1.9331711969931729,0.8202738098439962]],[[-0.25620764111264005,-2.0843122713824576],[-3.857637417314163e-16,-2.1],[0.25620764111264116,-2.084312271382457]],[[0.5190601482487361,1.3912499999999999],[4.277776428730301e-17,1.2000000000000002],[-0.5190601482487365,1.3912500000000005]],[[-1.6769635558805331,1.2640384615384619],[-1.1254855774029462,1.5777152587144616],[-0.5190601482487365,1.39125]],[[0.5190601482487364,1.39125],[1.125485577402946,1.5777152587144618],[1.6769635558805327,1.2640384615384623]],[[-1.4643879171394687,-0.24610572552447713],[-1.0392304845413263,-0.5999999999999996],[-0.9453277688907327,-1.145144274475522]],[[-1.4643879171394687,-0.24610572552447701],[-1.9290842826865349,0.18584147226671843],[-1.9331711969931735,0.8202738098439966]],[[-0.2562076411126403,-2.0843122713824584],[-0.8035987052835889,-1.7635567309811797],[-0.945327768890732,-1.1451442744755223]],[[0.9453277688907324,-1.1451442744755223],[1.0392304845413265,-0.5999999999999998],[1.464387917139469,-0.24610572552447735]],[[0.9453277688907326,-1.1451442744755225],[0.8035987052835892,-1.7635567309811797],[0.25620764111264155,-2.084312271382458]],[[1.933171196993173,0.8202738098439966],[1.929084282686535,0.1858414722667189],[1.4643879171394687,-0.2461057255244769]]];
function crushHole(context is Context,id is Id,target is Query,p is Vector,axis is Vector,depth,scale)
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(p*millimeter,axis,abs(axis[0])>0.9?vector(0,1,0):vector(1,0,0))});
 var i=0;for(var arc in M3_HYBRID_ARCS){i+=1;skArc(sk,"a"~i,{"start":vector(arc[0][0],arc[0][1])*scale*millimeter,"mid":vector(arc[1][0],arc[1][1])*scale*millimeter,"end":vector(arc[2][0],arc[2][1])*scale*millimeter});}
 skSolve(sk);opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":axis,"endBound":BoundingType.BLIND,"endDepth":depth*millimeter});cut(context,id+"cut",target,solid(context,id));opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
}
// Native original GT2 outline: 0.605/1.05/0.1 mm arcs, six teeth per clamp.
const GT2_TOOTH_ARCS = [[[1.2878587085651816e-13,0.2603579509350027],[0.02470348469293615,0.32616399003929075],[0.08660869565201779,0.35945725954943697]],[[0.08660869565201779,0.35945725954943697],[0.2502289562220108,0.3950399300438576],[0.4061123595516314,0.45617977527631126]],[[0.4061123595516314,0.45617977527631126],[0.7460000000001692,0.9999999999961204],[0.40611235954960545,1.5438202247146577]],[[0.40611235954960545,1.5438202247146577],[0.25022895622136954,1.604960069950181],[0.08660869565204532,1.6405427404506057]],[[0.08660869565204532,1.6405427404506057],[0.02470348469292194,1.6738360099606808],[1.0835776720341528e-13,1.7396420490649973]]];
function beltSocket(context is Context,id is Id,target is Query,z0,z1)
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(vector(0,11.9,0)*millimeter,vector(0,-1,0),vector(1,0,0))});
 var num=0;for(var h=z0;h<z1-0.1;h+=2){
  skLineSegment(sk,"lead"~num,{"start":vector(23.95,h)*millimeter,"end":vector(23.95+GT2_TOOTH_ARCS[0][0][0],h+GT2_TOOTH_ARCS[0][0][1])*millimeter});
  for(var arc in GT2_TOOTH_ARCS){num+=1;skArc(sk,"arc"~num,{"start":vector(23.95+arc[0][0],h+arc[0][1])*millimeter,"mid":vector(23.95+arc[1][0],h+arc[1][1])*millimeter,"end":vector(23.95+arc[2][0],h+arc[2][1])*millimeter});}
  skLineSegment(sk,"tail"~num,{"start":vector(23.95+GT2_TOOTH_ARCS[4][2][0],h+GT2_TOOTH_ARCS[4][2][1])*millimeter,"end":vector(23.95,h+2)*millimeter});
 }
 skLineSegment(sk,"top",{"start":vector(23.95,z1)*millimeter,"end":vector(25.5,z1)*millimeter});
 skLineSegment(sk,"back",{"start":vector(25.5,z1)*millimeter,"end":vector(25.5,z0)*millimeter});
 skLineSegment(sk,"bottom",{"start":vector(25.5,z0)*millimeter,"end":vector(23.95,z0)*millimeter});skSolve(sk);
 opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":vector(0,1,0),"endBound":BoundingType.BLIND,"endDepth":6.2*millimeter});cut(context,id+"cut",target,solid(context,id));opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
}
function beltJaw(context is Context,id is Id,z0) returns Query
{
 // Retain the native screw-hole profile; add a continuous rear wall.
 var jaw=rect(context,id+"blank",20.5,6.3,z0,24.9,19.5,z0+12);
 productCorners(context,id+"exposedCorners",jaw,1,0.4,{"coordinate":0,"value":20.5});
 beltSocket(context,id+"teeth",jaw,z0,z0+12);
 // Small jaws are identified in the manual; omit microtext on the thin back wall.
 for(var h in [3,9])crushHole(context,id+("thread"~h),jaw,vector(25,9.6,z0+h),vector(-1,0,0),4.6,1);
 // 0.4 mm initial closing clearance to the main body; the screw clamps the actual belt.
 opTransform(context,id+"openGap",{"bodies":jaw,"transform":transform(vector(-0.2,0,0)*millimeter)});return jaw;
}
function hexNutBlank(context is Context,id is Id,p is Vector,axis is Vector,af,h) returns Query
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(p*millimeter,axis,vector(1,0,0))});
 for(var i=0;i<6;i+=1)skLineSegment(sk,"e"~i,{"start":vector(cos(i*60*degree),sin(i*60*degree))*af/sqrt(3)*millimeter,"end":vector(cos((i+1)*60*degree),sin((i+1)*60*degree))*af/sqrt(3)*millimeter});
 skSolve(sk);opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":axis,"endBound":BoundingType.BLIND,"endDepth":h*millimeter});
 opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});return solid(context,id);
}
function hexNut(context is Context,id is Id,p is Vector,axis is Vector) returns Query
{return hexNutSized(context,id,p,axis,5.5,2.4,1.5);}
function hexNutSized(context is Context,id is Id,p is Vector,axis is Vector,af,thickness,r) returns Query
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(p*millimeter,axis,abs(axis[0])>0.9?vector(0,1,0):vector(1,0,0))});
 for(var i=0;i<6;i+=1)skLineSegment(sk,"e"~i,{"start":vector(cos(i*60*degree),sin(i*60*degree))*af/sqrt(3)*millimeter,"end":vector(cos((i+1)*60*degree),sin((i+1)*60*degree))*af/sqrt(3)*millimeter});
 skSolve(sk);opExtrude(context,id+"extrude",{"entities":qSketchRegion(id+"sk"),"direction":axis,"endBound":BoundingType.BLIND,"endDepth":thickness*millimeter});
 var q=solid(context,id+"extrude");opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
 cut(context,id+"bore",q,cyl(context,id+"boreTool",p-axis*0.1,axis,r,thickness+0.2));return q;
}
function screw(context is Context,id is Id,p is Vector,axis is Vector,len) returns Query
{
 var q=cyl(context,id+"shaft",p-axis*0.1,axis,1.5,len+0.1);join(context,id+"headJoin",q,cyl(context,id+"head",p-axis*3,axis,2.75,3));
 cut(context,id+"socket",q,cyl(context,id+"socketTool",p-axis*3.1,axis,1.25,1.6));return q;
}
// A continuous stepped wall connects the wagon plate to the belt frame.
// Keep the existing laser-side seating planes and 0.2 mm slider/jaw clearance.
// The 29 mm central span stays between the idler and drive pulley at full travel.
function wagonLoadBridge(context is Context,id is Id,z) returns Query
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(vector(0,0,z-14.5)*millimeter,vector(0,0,1),vector(1,0,0))});
 var pts=[vector(8,19),vector(19.9,19),vector(19.9,19.7),vector(29.2,19.7),vector(29.2,25.5),vector(19,25.5),vector(19,22.5),vector(8,22.5)];
 for(var i=0;i<size(pts);i+=1)skLineSegment(sk,"e"~i,{"start":pts[i]*millimeter,"end":pts[(i+1)%size(pts)]*millimeter});
 skSolve(sk);
 opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":vector(0,0,1),"endBound":BoundingType.BLIND,"endDepth":29*millimeter});
 opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
 return solid(context,id);
}
annotation { "Feature Type Name" : "Sparky X/Z R16 - Endstop Clearance" }
export const sparkyZ = defineFeature(function(context is Context,id is Id,definition is map)
precondition
{
 annotation { "Name" : "Carriage position (mm), operating 24 to 120" } isLength(definition.position,LENGTH_BOUNDS);
 annotation { "Name" : "Rail length" } isLength(definition.railLength,LENGTH_BOUNDS);
 annotation { "Name" : "Carriage hole pitch X - verify MGN9H" } isLength(definition.pitchX,LENGTH_BOUNDS);
 annotation { "Name" : "Carriage hole pitch Z - verify MGN9H" } isLength(definition.pitchZ,LENGTH_BOUNDS);
 annotation { "Name" : "Rail first hole from end - measure" } isLength(definition.railEnd,LENGTH_BOUNDS);
 annotation { "Name" : "Pulley center distance" } isLength(definition.driveCenters,LENGTH_BOUNDS);
 annotation { "Name" : "Stowed probe above nozzle - calibrate actual 3D Touch" } isLength(definition.probeClearance,PROBE_CLEARANCE);
 annotation { "Name" : "Probe pin deployed - reference envelope" } definition.probeDeployed is boolean;
 annotation { "Name" : "Belt tensioner pull down - 0 to 6 mm" } isLength(definition.beltAdjust,BELT_ADJUST);
 annotation { "Name" : "Show reference hardware" } definition.hardware is boolean;
}
{
 var guideLift=10; // Coordinated guide lift; laser and probe work coordinates are compensated.
 var z=definition.position/millimeter;var length=definition.railLength/millimeter;
 var hx=definition.pitchX/millimeter/2;var hz=definition.pitchZ/millimeter/2;
 var end=definition.railEnd/millimeter;var motorZ=definition.driveCenters/millimeter;
 var orange=color(0.88,0.36,0.12);var dark=color(0.20,0.24,0.28);var steel=color(0.66,0.71,0.75);
 // 40.3 mount-to-stowed and 46.6 mount-to-deployed from ANTCLABS V3.1 drawing.
 // These axial dimensions are provisional for the user's 3D Touch V3.2 clone.
 var nozzleZ=z-71.5-guideLift;var probeTop=nozzleZ+definition.probeClearance/millimeter+40.3;
 var probeX=-30.25;var probeY=28.3;var probeAngle=50*degree;var driveShift=-6.5;var homeShift=length-200;
 var slideZ=z+3-definition.beltAdjust/millimeter;
 var stage="base";
 try {
 var base=rect(context,id+"base",-40,0,-10,40,6,length+10);productCorners(context,id+"baseCorners",base,1,2,{});productFaceEdge(context,id+"baseFaceEdge",base,1,6,0.4);
 // Permanent connected X carrier occupies the old 6 mm plate envelope.
 var xCarrier=rect(context,id+"xLeft",-35,0,24,-18,6,88);
 join(context,id+"xCrossJoin",xCarrier,rect(context,id+"xCross",-34.9,0,52.5,34.9,3,59.5));
 join(context,id+"xRightJoin",xCarrier,rect(context,id+"xRight",18,0,24,35,6,88));
 // R11: continuous 96 mm stepped inner ledges and 6 mm deep fastening pads.
 for(var side in [-1,1]){
  var x0=side<0?-20:12;var x1=side<0?-12:20;
  join(context,id+("xLedgeJoin"~side),xCarrier,rect(context,id+("xLedge"~side),x0,0,8,x1,3,104));
 }
 var xt=0;for(var tab in [[-39.8,8,-25,32],[-39.8,80,-25,104],[25,8,39.8,32],[25,80,39.8,104]]){xt+=1;var pad=rect(context,id+("xTab"~xt),tab[0],-4,tab[1],tab[2],2,tab[3]);productCorners(context,id+("xTabRound"~xt),pad,1,1.2,{});productFaceEdge(context,id+("xTabFaceEdge"~xt),pad,1,-4,0.4);join(context,id+("xTabJoin"~xt),xCarrier,pad);}
 // R12: tie each pad directly to its continuous inner ledge, in the existing lap.
 // These short, broad webs bypass the relieved shoulders beside the wheel axles.
 for(var side in [-1,1])for(var h in [8,88]){
  var wx0=side<0?-27:18;var wx1=side<0?-18:27;
  join(context,id+("xPadWebJoin"~side~h),xCarrier,rect(context,id+("xPadWeb"~side~h),wx0,0,h,wx1,2,h+16));
 }
 // Free the entire 6 mm front spacer, including eccentric rotation, to the Y=0 seat.
 // Upper side-entry pocket: room for a SW10 wrench, 4 mm thick / 18 mm head / 30 degree swing.
 // The tool pocket leaves 0.8 mm of the rear reinforcement and the main plate intact.
 for(var x in [-27,27]){
  for(var h in [35.846,76.346])holeY(context,id+("frontSpacerClear"~x~h),xCarrier,x,h,7.5,-4.1,4.1);
  holeY(context,id+("eccentricWrenchRound"~x),xCarrier,x,76.346,10.75,-4.1,3.3);
  var sx0=x<0?-41:27;var sx1=x<0?-27:41;
  cut(context,id+("eccentricWrenchEntry"~x),xCarrier,rect(context,id+("eccentricWrenchEntryTool"~x),sx0,-4.1,65.596,sx1,-0.8,89.1));
 }
 // Exact X-carriage interface extracted from Fusion. Upper holes clear eccentric spacers.
 for(var x in [-27,27])for(var h in [35.846,76.346]){
  var n="mount"~x~h;holeY(context,id+n,xCarrier,x,h,h<50?2.6:3.6,-1,8);
  holeY(context,id+n+"head",xCarrier,x,h,h<50?5:6,3,4);
 }
 for(var h=end;h<length;h+=20)crushHole(context,id+("railThread"~h),base,vector(0,6.1,h),vector(0,-1,0),6.2,1);
 holeY(context,id+"motorPilot",base,18.5,motorZ,11.2,-1,8);
 // Only the two right mounting screws are accessible and used on the real motor.
 for(var h in [-15.5,15.5])holeY(context,id+("motor15.5"~h),base,34,motorZ+h,1.7,-1,8);
 // Keep legacy motor-hole IDs contiguous before creating the recess operations.
 // A 3.2 mm pocket buries each 3 mm head by 0.2 mm and leaves a 2.8 mm floor.
 for(var h in [-15.5,15.5])holeY(context,id+("motorHeadRecess"~h),base,34,motorZ+h,3.1,2.8,3.3);
 // Original PCB endstop: 15 mm fixing pitch. Separate from removed Omron probe.
 // Homing mount is integral with the Z plate; no mounting holes/nuts.
 // One-piece axle pedestal: broad support stops short of the rotating pulley.
 var boss=rect(context,id+"idlerBoss",10.5,6,-10,34,9.5,6);productCorners(context,id+"idlerBossCorners",boss,1,1.2,{});productFaceEdge(context,id+"idlerBossFaceEdge",boss,1,9.5,0.4);
 join(context,id+"idlerBossJoin",base,boss);
 join(context,id+"idlerInnerRaceSeat",base,cyl(context,id+"idlerSeat",vector(18.5,9.5,0),vector(0,1,0),3.3,0.5));
 holeY(context,id+"idlerThroughAxle",base,18.5,0,2.7,-1,12);
 nutY(context,id+"idlerRearM5Nut",base,18.5,0,8.3,0,4.5);
 // Symmetric motor clearance, with guide and axle lifted clear above the motor bodies.
 cut(context,id+"leftMotorClear",base,rect(context,id+"leftMotorClearTool",-41,-0.1,-11,-14,10,3.5-guideLift));
 cut(context,id+"rightMotorClear",base,rect(context,id+"rightMotorClearTool",14,-0.1,-11,41,10,3.5-guideLift));
 // Open side cutouts leave the four wheel fasteners entirely on the X carrier.
 cut(context,id+"xLeftRelease",base,rect(context,id+"xLeftReleaseTool",-41,-0.1,23.8-guideLift,-17.8,6.1,88.2-guideLift));
 cut(context,id+"xRightRelease",base,rect(context,id+"xRightReleaseTool",17.8,-0.1,23.8-guideLift,41,6.1,88.2-guideLift));
 cut(context,id+"xCrossRelease",base,rect(context,id+"xCrossReleaseTool",-18,-0.1,52.3-guideLift,18,3.2,59.7-guideLift));
 var xc=0;for(var tab in [[-39.8,8,-25,32],[-39.8,80,-25,104],[25,8,39.8,32],[25,80,39.8,104]]){xc+=1;cut(context,id+("xLapCut"~xc),base,rect(context,id+("xLapTool"~xc),tab[0]-0.2,-0.1,tab[1]-0.2-guideLift,tab[2]+0.2,2,tab[3]+0.2-guideLift));}
 for(var side in [-1,1])for(var h in [8,88]){
  var wx0=side<0?-27.2:17.8;var wx1=side<0?-17.8:27.2;
  cut(context,id+("zPadWebClear"~side~h),base,rect(context,id+("zPadWebTool"~side~h),wx0,-0.1,h-0.2-guideLift,wx1,2.2,h+16.2-guideLift));
 }
 // Broad continuous stepped seating beside the central rail spine.
 for(var side in [-1,1]){
  var x0=side<0?-20.2:11.8;var x1=side<0?-11.8:20.2;
  cut(context,id+("zLedgeCut"~side),base,rect(context,id+("zLedgeTool"~side),x0,-0.1,7.8-guideLift,x1,3,104.2-guideLift));
 }
 for(var joint in [[-36,16],[-36,96],[36,16],[36,96]]){
  var jn="xJoint"~joint[0]~joint[1];holeY(context,id+jn+"clear",base,joint[0],joint[1]-guideLift,1.7,1.9,4.2);
  crushHole(context,id+jn+"thread",xCarrier,vector(joint[0],2.1,joint[1]),vector(0,-1,0),6.2,1);
 }
 holeY(context,id+"lowerRightJointHeadClear",base,36,16-guideLift,3.1,6,4.2);
 productMark(context,id+"xCarrierId",xCarrier,"09",vector(-29.5,-4,96),vector(0,-1,0),vector(1,0,0),6,5);
 productMark(context,id+"xAxisMark",xCarrier,"x",vector(0,0,56),vector(0,-1,0),vector(1,0,0),4.5,4.5);
 productMark(context,id+"baseId",base,"01",vector(-14,0,length+5),vector(0,-1,0),vector(1,0,0),6,5);
 productMark(context,id+"baseRevision",base,"r16",vector(-28,0,length+5),vector(0,-1,0),vector(1,0,0),8,5);
 productMark(context,id+"zAxisMark",base,"z",vector(-30,6,length-43),vector(0,1,0),vector(-1,0,0),5,5);
 productArrowY(context,id+"zAxisArrow",base,-30,6,length-54,10,3);
 cut(context,id+"raisedIdlerCarrierClear",xCarrier,rect(context,id+"raisedIdlerCarrierClearTool",11.8,-0.1,7.8,24.2,3.2,16.5));
 holeY(context,id+"railTipCarrierRelief",xCarrier,0,60,1.9,0.8,2.5);
 namePart(context,xCarrier,"09 X Carrier R16",color(0.62,0.61,0.57));
 namePart(context,base,"01 Z Base R16",color(0.62,0.61,0.57));

 stage="moving carriage";
 var car=rect(context,id+"car",-24,16,z-30,36,29,z+30);productCorners(context,id+"carCorners",car,1,2,{});productFaceEdge(context,id+"carRearEdge",car,1,16,0.4);productFaceEdge(context,id+"carFrontEdge",car,1,29,0.4);
 cut(context,id+"beltRearRelief",car,rect(context,id+"relief",10,15,z-31,37,23,z+31));
 join(context,id+"centralRearBridgeJoin",car,rect(context,id+"centralRearBridge",8,19,z-13.5,19.9,25.5,z+13.5));
 cut(context,id+"lowerStopRelief",car,rect(context,id+"lowerStopReliefTool",-10.5,15,z-31,10.5,18.5,z-20));
 var pocket=rect(context,id+"sensorFlangePocket",-25,15,z-31,-20.4,30,z-25.5);roundY(context,id+"sensorFlangePocketRound",pocket,1);
 cut(context,id+"sensorFlangePocketCut",car,pocket);
 var lowerRightEar=rect(context,id+"lowerRightJoiningPad",29,19,z-30,39.5,29,z-17);
 productCorners(context,id+"lowerRightJoiningPadRound",lowerRightEar,1,1.2,{});join(context,id+"lowerRightJoiningPadJoin",car,lowerRightEar);
 var leftEar=rect(context,id+"leftJoiningFlange",-31,16,z+5,-19,29,z+30);
 productCorners(context,id+"leftJoiningFlangeRound",leftEar,1,1.2,{});
 join(context,id+"leftJoiningFlangeJoin",car,leftEar);
 // Join after the flange exists: uninterrupted pad left of the screw axes.
 join(context,id+"homeCamJoin",car,rect(context,id+"homeCam",-38,12,z+9,-30,32.5,z+15.5));
 // Rear-loading open-belt anchors with a continuous 6 mm front plate and a T-guided upper slider.
 // Right-side structure remains inside the 80 mm backplate width.
 join(context,id+"tensionFrameJoin",car,rect(context,id+"tensionFrame",28.5,9,z-15,39.5,29,z+30));
 // T-slot: 0.3 mm lateral running clearance, open at the top for assembly.
 cut(context,id+"tensionGuideCut",car,rect(context,id+"tensionGuide",28.7,12.3,z-3,35.4,19.7,z+31));
 cut(context,id+"tensionMouthCut",car,rect(context,id+"tensionMouth",19.9,6.8,z-3,29.2,19.7,z+31));
 // Fixed lower end: six teeth; both sockets load from -Y, before mounting the carriage.
 join(context,id+"fixedAnchorJoin",car,rect(context,id+"fixedAnchor",25.1,6.3,z-15,33.2,23,z-3));
 beltSocket(context,id+"fixedSocket",car,z-15,z-3);
 for(var h in [-12,-6]){
  cut(context,id+("fixedClampClear"~h),car,cyl(context,id+("fixedClampBore"~h),vector(24.8,9.6,z+h),vector(1,0,0),1.7,16));
  cut(context,id+("fixedClampHeadClear"~h),car,cyl(context,id+("fixedClampHead"~h),vector(33.2,9.6,z+h),vector(1,0,0),2.9,12));
 }
 // One rear-open head-access window removes the 0.2 mm web and tangent remnants.
 // R16: 8.1 mm fixed support, extended by 4 mm along the screw axes.
 // The seating shoulder is X33.2; working guide faces still start at Y12.5.
 cut(context,id+"fixedClampAccessWindow",car,rect(context,id+"fixedClampAccessTool",33.2,6.2,z-15.1,41,12.5,z-2.9));
 // Tool opening stays behind the T-guide's main bearing faces and continuous front wall.
 cut(context,id+"movingClampHeadAccess",car,rect(context,id+"movingClampHeadTool",29.1,6.5,z-2.9,41,12.5,z+16));
 // The thick lower ledge reacts the pull screw; the driver approaches from above.
 crushHole(context,id+"tensionFrameThread",car,vector(31.8,16,z-2.9),vector(0,0,-1),12.2,1);

 cut(context,id+"idlerHeadTravelRelief",car,rect(context,id+"idlerHeadTravelTool",13.5,22,z-31,23.5,26,z-13));
 // Stepped separation: 6.5 mm laser plate centrally; 3.5 mm over the belt frame.
 // The rear frame therefore retains its continuous front wall and full T guide.
 var splitTool=rect(context,id+"splitCentral",-45,22.5,z-40,19,50,z+40);
 join(context,id+"splitToolJoin",splitTool,rect(context,id+"splitRight",18.9,25.5,z-40,45,50,z+40));
 opPattern(context,id+"laserPlateCopy",{"entities":car,"transforms":[identityTransform()],"instanceNames":["laserHalf"]});
 var laserPlate=solid(context,id+"laserPlateCopy");
 stage="stepped adapter split";
 opBoolean(context,id+"rearPlateSeparation",{"targets":car,"tools":splitTool,"operationType":BooleanOperationType.SUBTRACTION,"keepTools":true});
 stage="intersect front half";
 opBoolean(context,id+"laserPlateIntersection",{"tools":qUnion([laserPlate,splitTool]),"operationType":BooleanOperationType.INTERSECTION});
 laserPlate=solid(context,id+"laserPlateIntersection");
 stage="continuous wagon load bridge";
 // Add only to the separated wagon half. Existing laser adapters remain compatible.
 join(context,id+"wagonLoadBridgeJoin",car,wagonLoadBridge(context,id+"wagonLoadBridge",z));
 stage="laser mounting holes";
 // Wagon screws are installed with the laser half removed.
 for(var x in [-hx,hx])for(var h in [-hz,hz]){
  var n="block"~x~h;holeY(context,id+n,car,x,z+h,1.7,15,8);holeY(context,id+n+"head",car,x,z+h,3.1,19.3,3.3);
 }

 for(var h in [-20,-6])crushHole(context,id+("sensorThread"~h),car,vector(-18,15.9,z+h),vector(0,1,0),6.7,1);
 // Continuous lower mounting pad for the compensated laser position.
 join(context,id+"laserLowerPadJoin",laserPlate,rect(context,id+"laserLowerPad",-14,22.5,z-34,14,29,z-20));
 // Flush rear heads; the laser half can be screwed to the laser on the bench.
 for(var x in [-8,8])for(var h in [-15,15]){
  var n="laser"~x~h;holeY(context,id+n,laserPlate,x,z+h-guideLift,1.7,22.4,7);
  holeY(context,id+n+"head",laserPlate,x,z+h-guideLift,3.1,22.4,3.3);
 }
 stage="joint mounting holes";
 var approachPocket=rect(context,id+"probeApproachPocket",-25,22.4,z-31,-20.4,40,z-18.5);roundY(context,id+"probeApproachPocketRound",approachPocket,1);cut(context,id+"probeApproachPocketCut",laserPlate,approachPocket);
 // Two upper-left and two right screws avoid the recessed BLTouch and laser body.
 for(var h in [10,24]){
  crushHole(context,id+("joinLeftThread"~h),car,vector(-25,22.6,z+h),vector(0,-1,0),6.7,1);
  holeY(context,id+("joinLeftFront"~h),laserPlate,-25,z+h,1.7,22.4,7);
  holeY(context,id+("joinLeftHeadClear"~h),laserPlate,-25,z+h,3.1,29,9);
 }
 for(var h in [-23,23]){
  crushHole(context,id+("joinRightThread"~h),car,vector(35,25.6,z+h),vector(0,-1,0),6.7,1);
  holeY(context,id+("joinRightFront"~h),laserPlate,35,z+h,1.7,25.4,4);
 }
 stage="registers";
 // Broad registers resist shear; 0.2 mm lateral and axial clearance for FDM.
 for(var h in [-18,25]){
  var key=rect(context,id+("register"~h),-5,22.4,z+h-1.5,5,24,z+h+1.5);
  join(context,id+("registerJoin"~h),car,key);
  cut(context,id+("registerSocket"~h),laserPlate,rect(context,id+("registerClearance"~h),-5.2,22.4,z+h-1.7,5.2,24.2,z+h+1.7));
 }
 for(var fragment in evaluateQuery(context,car))if(evVolume(context,{"entities":fragment})<0.00001*millimeter^3)opDeleteBodies(context,id+"splitToleranceFragment",{"entities":fragment});
 productMark(context,id+"carId",car,"02",vector(-5,16,z+25),vector(0,-1,0),vector(1,0,0),6,5);
 productMark(context,id+"beltMark",car,"belt",vector(39.5,22.5,z+9),vector(1,0,0),vector(0,0,1),17,4.5);
 productMark(context,id+"laserPlateId",laserPlate,"04",vector(-25,29,z+17),vector(0,1,0),vector(-1,0,0),6,5);
 // Clear the Y-endstop housing at the back of the Z-home cam; retain its front actuation face.
 cut(context,id+"homeCamRearCornerClear",car,rect(context,id+"homeCamRearCornerTool",-40,11.9,z+8.9,-36,14.8,z+15.6));
 namePart(context,car,"02 Wagon Adapter R16",color(0.18,0.19,0.185));
 namePart(context,laserPlate,"04 Laser Adapter R16",color(0.18,0.19,0.185));
 var clamp=rect(context,id+"clamp",25.1,6.3,slideZ,29,19.5,slideZ+12);
 productCorners(context,id+"sliderExposedCorners",clamp,1,0.4,{"coordinate":0,"value":29});
 join(context,id+"sliderTongueJoin",clamp,rect(context,id+"sliderTongue",28.5,12.5,slideZ,35.2,19.5,slideZ+12));
 beltSocket(context,id+"movingSocket",clamp,slideZ,slideZ+12);
 cut(context,id+"sliderPullBore",clamp,cyl(context,id+"sliderPullTool",vector(31.8,16,slideZ-1),vector(0,0,1),1.7,16));
 for(var h in [3,9])cut(context,id+("movingClampClear"~h),clamp,cyl(context,id+("movingClampBore"~h),vector(24.8,9.6,slideZ+h),vector(1,0,0),1.7,5));
 // Omit the small rear-face ID instead of engraving into the screw-hole wall.
 namePart(context,clamp,"03 Belt Tension Slider R16",color(1,0.12,0.008));
 var lowerJaw=beltJaw(context,id+"lowerBeltJaw",z-15);namePart(context,lowerJaw,"10 Belt Clamp Jaw R16 - fixed",color(1,0.12,0.008));
 var upperJaw=beltJaw(context,id+"upperBeltJaw",slideZ);namePart(context,upperJaw,"10 Belt Clamp Jaw R16 - moving",color(1,0.12,0.008));
 stage="integral narrow rail stops";
 var bottomStop=rect(context,id+"bottomRailStop",-4.5,5.8,-10,4.5,18,0);
 var topStop=rect(context,id+"topRailStop",-4.5,5.8,length,4.5,18,length+10);
 join(context,id+"bottomRailStopJoin",base,bottomStop);join(context,id+"topRailStopJoin",base,topStop);

 stage="compact probe arm";
 // A 2 mm track-end cap replaces the former 0.5 mm cap; full adjustment travel remains.
 var arm=rect(context,id+"arm",-35.5,10,z-36-guideLift,-12,16,z+3.5);productCorners(context,id+"armCorners",arm,1,1.2,{});productFaceEdge(context,id+"armFrontEdge",arm,1,16,0.4);productFaceEdge(context,id+"armRearEdge",arm,1,10,0.4);
 for(var h in [-20,-6])holeY(context,id+("armBolt"~h),arm,-18,z+h,1.7,9,8);
 for(var h in [-16.9,-4.9]){
  var slot=rect(context,id+("probeSlot"~h),-32.2,9,z+h-4.7-guideLift,-28.8,17,z+h+4.7-guideLift);
  roundY(context,id+("probeSlotRound"~h),slot,1.699);cut(context,id+("probeSlotCut"~h),arm,slot);
 }
 for(var x in [-33.5,-25])cut(context,id+("cableTieCut"~x),arm,rect(context,id+("cableTie"~x),x,9,z-32-guideLift,x+3,17,z-29-guideLift));
 // Shared rectangular track: M3 flats slide vertically without spinning.
 // Depth 2.6 in the 6 mm plate leaves a continuous 3.4 mm clamping wall.
 cut(context,id+"probeNutTrackCut",arm,rect(context,id+"probeNutTrack",-33.4,9.9,z-23.3-guideLift,-27.6,12.6,z+1.5-guideLift));
 productMark(context,id+"armId",arm,"06",vector(-18,10,z-30),vector(0,-1,0),vector(1,0,0),6,5);
 productMark(context,id+"probeMark",arm,"probe",vector(-35.5,13,z-13),vector(-1,0,0),vector(0,0,1),23,4.5);
 namePart(context,arm,"06 Probe Arm R16",color(0.18,0.19,0.185));

 stage="recessed side probe bracket";
 var tray=rect(context,id+"tray",-39,16,probeTop,-24,43,probeTop+5);productCorners(context,id+"trayCorners",tray,2,1.2,{});productFaceEdge(context,id+"trayDeckEdge",tray,2,probeTop+5,0.4);
 var wing=rect(context,id+"trayWing",-27,30,probeTop,-21,43,probeTop+5);productCorners(context,id+"trayWingRound",wing,2,1.2,{});join(context,id+"trayWingJoin",tray,wing);
 var tab=rect(context,id+"trayTab",-39,16,probeTop,-24,21,probeTop+30);productCorners(context,id+"probeTabCorners",tab,1,1.2,{});join(context,id+"trayTabJoin",tray,tab);
 // Keep the outer load-carrying rib; omit the inner rib severed by screw access.
 for(var x in [-39])join(context,id+("probeRibJoin"~x),tray,gussetX(context,id+("probeRib"~x),x,20,probeTop+4));
 for(var h in [11,23])holeY(context,id+("probeSlideBolt"~h),tray,-30.5,probeTop+h,1.7,15,7);
 for(var sign in [-1,1]){
  var p=vector(probeX+sign*9*cos(probeAngle),probeY+sign*9*sin(probeAngle),probeTop);
  crushHole(context,id+("probeFlangeThread"~sign),tray,p-vector(0,0,0.1),vector(0,0,1),5.2,1);
 }
 cut(context,id+"probeCoreAccessCut",tray,cyl(context,id+"probeCoreAccess",vector(probeX,probeY,probeTop-1),vector(0,0,1),3.5,7));
 productMark(context,id+"trayId",tray,"07",vector(-31.5,23,probeTop),vector(0,0,-1),vector(1,0,0),7,5);
 productArrowY(context,id+"probeHeightArrow",tray,-25.3,21,probeTop+17,12,2);
 // Local back-edge relief clears the X-endstop PCB; the outer supporting rib starts beyond Y20.
 cut(context,id+"probeTabEndstopClear",tray,rect(context,id+"probeTabEndstopTool",-40,15.9,probeTop-0.1,-37.2,20,probeTop+30.1));
 namePart(context,tray,"07 Probe Bracket R16",color(1,0.12,0.008));

 stage="forward offset upper endstop mount";
 // One rectangular integral boss; the old mounting island and L-shaped rib are obsolete.
 var home=rect(context,id+"homeBoss",-32,5.8,length-6.5,-24,34,length+10);
 productFaceEdge(context,id+"homeTopEdge",home,2,length+10,0.4);
 productMark(context,id+"homeMark",home,"home",vector(-28,21,length+10),vector(0,0,1),vector(0,1,0),21,5);
 // Former attachment holes are filled by the integral mount.
 for(var y in [14.5,29.5])crushHole(context,id+("homePcbThread"~y),home,vector(-32.1,y,length-2),vector(1,0,0),5.2,2.5/3);
 join(context,id+"integralHomeMountJoin",base,home);

 if(definition.hardware){
 stage="reference hardware";
 // Include both motor screws in the main model, not only the guide steps.
 // M3x6 at Y2.8 gives nominal 3.2 mm motor engagement; verify the actual motor.
 for(var h in [-15.5,15.5])namePart(context,screw(context,id+("zMotorMountScrew"~h),vector(34,2.8,motorZ+h),vector(0,-1,0),6),"REF Z Motor M3x6 right mounting screw "~h~" - verify thread depth",steel);
 for(var joint in [[-36,16],[-36,96],[36,16],[36,96]])namePart(context,screw(context,id+("xJointScrew"~joint[0]~joint[1]),vector(joint[0],6,joint[1]),vector(0,-1,0),10),"REF X Joint M3x10 screw "~joint[0]~" "~joint[1],steel);
 var rail=rect(context,id+"rail",-4.5,6,0,4.5,12.5,length);
 for(var h=end;h<length;h+=20){holeY(context,id+("rh"~h),rail,0,h,1.75,5,9);holeY(context,id+("rcb"~h),rail,0,h,3,9,5);}
 namePart(context,rail,"REF MGN9 rail 160 - verify end-hole offset",steel);
 // Nominal screws previously present only in guide steps; rail holes use the same measured offset.
 for(var h=definition.railEnd/millimeter;h<=length;h+=20)
  namePart(context,screw(context,id+("railMountScrew"~h),vector(0,9,h),vector(0,-1,0),8),"REF Rail M3x8 mounting screw "~h~" - verify actual length",steel);

 var block=rect(context,id+"block",-10,8,z-19.95,10,16,z+19.95);
 cut(context,id+"blockGroove",block,rect(context,id+"blockGrooveTool",-4.6,7,z-21,4.6,12.6,z+21));
 for(var x in [-hx,hx])for(var h in [-hz,hz])holeY(context,id+("blockThread"~x~h),block,x,z+h,1.5,13,4);
 namePart(context,block,"REF MGN9H envelope 20 x 39.9 - provisional",steel);
 // The belt is OPEN at the carriage. Show separate ends, never a continuous run through the tensioner.
 var returnBelt=rect(context,id+"returnBelt",11.444,12,0,12.824,18,motorZ);
 namePart(context,returnBelt,"REF GT2 6 mm belt - return run",color(0.08,0.09,0.10));
 var lowerBelt=rect(context,id+"lowerBelt",24.176,12,0,25.556,18,z-3);
 namePart(context,lowerBelt,"REF GT2 6 mm belt - lower fixed end",color(0.08,0.09,0.10));
 var upperBelt=rect(context,id+"upperBelt",24.176,12,slideZ,25.556,18,motorZ);
 namePart(context,upperBelt,"REF GT2 6 mm belt - upper adjustable end",color(0.08,0.09,0.10));
 stage="separate adapter mounting fasteners";
 for(var x in [-hx,hx])for(var h in [-hz,hz])namePart(context,screw(context,id+("wagonScrew"~x~h),vector(x,19.3,z+h),vector(0,-1,0),6),"REF Adapter M3x6 wagon screw "~x~" "~h,steel);
 for(var x in [-8,8])for(var h in [-15,15])namePart(context,screw(context,id+("laserScrew"~x~h),vector(x,25.7,z+h-guideLift),vector(0,1,0),6),"REF Adapter M3x6 laser screw "~x~" "~h,steel);
 for(var h in [10,24]){
  namePart(context,screw(context,id+("joinLeftScrew"~h),vector(-25,29,z+h),vector(0,-1,0),12),"REF Adapter M3x12 left joint screw "~h,steel);
 }
 for(var h in [-23,23]){
  namePart(context,screw(context,id+("joinRightScrew"~h),vector(35,29,z+h),vector(0,-1,0),10),"REF Adapter M3x10 right joint screw "~h,steel);
 }
 stage="belt tensioner and idler fasteners";
 var pull=screw(context,id+"beltPullScrew",vector(31.8,16,slideZ+12.5),vector(0,0,-1),35);
 namePart(context,pull,"REF Tension M3x35 screw - access above",steel);
 var tw=cyl(context,id+"beltPullWasher",vector(31.8,16,slideZ+12),vector(0,0,1),3.5,0.5);
 cut(context,id+"beltPullWasherBore",tw,cyl(context,id+"beltPullWasherTool",vector(31.8,16,slideZ+11.9),vector(0,0,1),1.6,0.7));namePart(context,tw,"REF Tension M3 pull washer",steel);
 // Fixed screws move out 4 mm and grow 4 mm; the jaw engagement and tips stay put.
 var bc=0;for(var pos in [[z-12,0],[z-6,0],[slideZ+3,1],[slideZ+9,1]]){
  bc+=1;var fixed=pos[1]==0;
  namePart(context,screw(context,id+("beltClampScrew"~bc),vector(fixed?33.2:29.2,9.6,pos[0]),vector(-1,0,0),fixed?12:8),fixed?"REF Belt Clamp M3x12 fixed screw "~bc:"REF Belt Clamp M3x8 moving screw "~bc,steel);
 }
 var axle=cyl(context,id+"idlerM5Shaft",vector(18.5,-0.1,0),vector(0,1,0),2.5,20);
 join(context,id+"idlerM5HeadJoin",axle,cyl(context,id+"idlerM5Head",vector(18.5,19.9,0),vector(0,1,0),4.25,5));
 cut(context,id+"idlerM5SocketCut",axle,hexNutBlank(context,id+"idlerM5Socket",vector(18.5,22.4,0),vector(0,1,0),4,3));
 namePart(context,axle,"REF Idler M5x20 axle screw",steel);
 var iw=cyl(context,id+"idlerShim",vector(18.5,19.4,0),vector(0,1,0),4,0.5);
 cut(context,id+"idlerShimBore",iw,cyl(context,id+"idlerShimTool",vector(18.5,19.3,0),vector(0,1,0),2.6,0.7));
 namePart(context,iw,"REF Idler shim 8 x 5.2 x 0.5 - inner race support",steel);
 namePart(context,hexNutSized(context,id+"idlerM5Nut",vector(18.5,0.5,0),vector(0,1,0),8,4,2.5),"REF Idler M5 rear captive nut",steel);
 stage="instantiate retained Fusion solids";
 var inst=newInstantiator(id+"retained");
 addInstance(inst,Retained::build,{"partQuery":qBodyType(qEverything(EntityType.BODY),BodyType.SOLID),"name":"source"});instantiate(context,inst);
 var actual=evaluateQuery(context,qBodyType(qCreatedBy(id+"retained",EntityType.BODY),BodyType.SOLID));
 stage="classify retained Fusion solids";
 var movingLaser=[];var actualMotor=[];
 var k=0;
 for(var body in actual){
  k+=1;var bb=evBox3d(context,{"topology":body,"tight":true});
  if(bb.minCorner[1]>28*millimeter){movingLaser=append(movingLaser,body);namePart(context,body,"REUSED Laser Tree component "~k,color(0.3,0.34,0.38));}
  else if(bb.minCorner[2]>150*millimeter){actualMotor=append(actualMotor,body);namePart(context,body,"REUSED NEMA17 and drive component "~k,steel);}
  else {namePart(context,body,"REUSED GT2 Idler",steel);opTransform(context,id+"idlerPosition",{"bodies":body,"transform":transform(vector(driveShift,0,-10)*millimeter)});}
 }
 stage="position retained Fusion solids";
 opTransform(context,id+"laserPosition",{"bodies":qUnion(movingLaser),"transform":transform(vector(0,0,z-61.28756-guideLift)*millimeter)});
 opTransform(context,id+"actualMotorPosition",{"bodies":qUnion(actualMotor),"transform":transform(vector(driveShift,0,motorZ-175)*millimeter)});
 stage="original PCB homing switch";
 var hi=newInstantiator(id+"homeHardware");addInstance(hi,Home::build,{"partQuery":qBodyType(qEverything(EntityType.BODY),BodyType.SOLID),"name":"source"});instantiate(context,hi);
 var hn=0;
 for(var b in evaluateQuery(context,qBodyType(qCreatedBy(id+"homeHardware",EntityType.BODY),BodyType.SOLID))){
  hn+=1;var bb=evBox3d(context,{"topology":b,"tight":true});
  namePart(context,b,bb.minCorner[2]<171*millimeter?"REUSED Homing lever - actuates near Z120":"REUSED Homing PCB component "~hn,bb.maxCorner[1]-bb.minCorner[1]<2*millimeter?color(0.1,0.48,0.25):dark);
 }
 var homeBodies=qBodyType(qCreatedBy(id+"homeHardware",EntityType.BODY),BodyType.SOLID);
 opTransform(context,id+"rotateHome",{"bodies":homeBodies,"transform":transform(matrix([[0,-1,0],[1,0,0],[0,0,1]]),vector(-22,47,homeShift+5)*millimeter)});
 stage="3D Touch reference envelope";
 // Simplified envelope, not an exact vendor CAD model of the TEQStone clone.
 var sk=newSketchOnPlane(context,id+"probeFlangeSk",{"sketchPlane":plane(vector(probeX,probeY,probeTop-2)*millimeter,vector(0,0,1),vector(1,0,0))});
 skEllipse(sk,"oval",{"center":vector(0,0)*millimeter,"majorAxis":vector(0,1),"majorRadius":13*millimeter,"minorRadius":5.75*millimeter});skSolve(sk);
 opExtrude(context,id+"probeHousing",{"entities":qSketchRegion(id+"probeFlangeSk"),"direction":vector(0,0,1),"endBound":BoundingType.BLIND,"endDepth":2*millimeter});
 opDeleteBodies(context,id+"probeFlangeClean",{"entities":qCreatedBy(id+"probeFlangeSk",EntityType.BODY)});var housing=solid(context,id+"probeHousing");
 join(context,id+"probeNeckJoin",housing,cyl(context,id+"probeNeck",vector(probeX,probeY,probeTop-11),vector(0,0,1),5,9.2));
 join(context,id+"probeBodyJoin",housing,rect(context,id+"probeBody",probeX-6.5,probeY-7,probeTop-36.3,probeX+6.5,probeY+7,probeTop-10));
 for(var y in [probeY-9,probeY+9])cut(context,id+("probeLugCut"~y),housing,cyl(context,id+("probeLug"~y),vector(probeX,y,probeTop-3),vector(0,0,1),1.6,4));
 cut(context,id+"probeGuideCut",housing,cyl(context,id+"probeGuide",vector(probeX,probeY,probeTop-37),vector(0,0,1),1.1,30));
 namePart(context,housing,"REF 3D Touch V3.2 housing - axial dimensions provisional",color(0.85,0.85,0.82));
 var pcb=rect(context,id+"probePcb",probeX+6.5,probeY-6,probeTop-33,probeX+8.1,probeY+6,probeTop-11);
 join(context,id+"probePlugJoin",pcb,rect(context,id+"probePlug",probeX+8,probeY-5,probeTop-23,probeX+13,probeY+5,probeTop-18));
 namePart(context,pcb,"REF 3D Touch PCB and plug clearance envelope",color(0.12,0.45,0.22));
 var tip=probeTop-(definition.probeDeployed?46.6:40.3);
 var pin=cyl(context,id+"probePin",vector(probeX,probeY,tip),vector(0,0,1),1,18);
 namePart(context,pin,definition.probeDeployed?"REF 3D Touch pin DEPLOYED":"REF 3D Touch pin STOWED",color(0.75,0.76,0.78));
 var a=probeAngle-90*degree;var rotation=matrix([[cos(a),-sin(a),0],[sin(a),cos(a),0],[0,0,1]]);
 opTransform(context,id+"probeAngle",{"bodies":qUnion([housing,pcb,pin]),"transform":transform(rotation,(vector(probeX,probeY,0)-rotation*vector(probeX,probeY,0))*millimeter)});
 var cableAxis=vector(sin(probeAngle),-cos(probeAngle),0);
 var cable=cyl(context,id+"probeCable",vector(probeX,probeY,probeTop-20.5)+cableAxis*13,cableAxis,2,10);
 namePart(context,cable,"REF 3D Touch cable exit - 4 mm diameter x 10 mm clearance",color(0.18,0.2,0.23));

 stage="probe mounting fasteners";
 for(var h in [-20,-6]){
  namePart(context,screw(context,id+("probeArmScrew"~h),vector(-18,10,z+h),vector(0,1,0),12),"REF Probe M3x12 arm screw "~h,steel);
 }
 for(var h in [11,23]){
  namePart(context,screw(context,id+("probeSlideScrew"~h),vector(-30.5,21.5,probeTop+h),vector(0,-1,0),14),"REF Probe M3x14 height screw "~h,steel);
  var nutOrigin=vector(-30.5,10.2,probeTop+h);
  var slidingNut=hexNut(context,id+("probeSlideNut"~h),nutOrigin,vector(0,1,0));
  var nr=matrix([[cos(30*degree),0,sin(30*degree)],[0,1,0],[-sin(30*degree),0,cos(30*degree)]]);
  opTransform(context,id+("probeNutFlats"~h),{"bodies":slidingNut,"transform":transform(nr,(nutOrigin-nr*nutOrigin)*millimeter)});
  namePart(context,slidingNut,"REF Probe M3 height nut "~h,steel);
  var w=cyl(context,id+("probeWasher"~h),vector(-30.5,21,probeTop+h),vector(0,1,0),3.5,0.5);cut(context,id+("probeWasherCut"~h),w,cyl(context,id+("probeWasherHole"~h),vector(-30.5,20.9,probeTop+h),vector(0,1,0),1.6,0.7));namePart(context,w,"REF Probe M3 height washer "~h,steel);
 }
 for(var sign in [-1,1]){
  var p=vector(probeX+sign*9*cos(probeAngle),probeY+sign*9*sin(probeAngle),probeTop);
  namePart(context,screw(context,id+("probeFlangeScrew"~sign),p-vector(0,0,2),vector(0,0,1),6),"REF Probe M3x6 flange screw "~sign,steel);
 }

 for(var y in [14.5,29.5]){
  var p=vector(-34.00001,y,length-2);var axis=vector(1,0,0);
  var bolt=cyl(context,id+("homePcbShaft"~y),p-axis*0.1,axis,1.25,6.1);
  join(context,id+("homePcbHeadJoin"~y),bolt,cyl(context,id+("homePcbHead"~y),p-axis*2.5,axis,2.25,2.5));
  namePart(context,bolt,"REF Home M2.5x6 PCB screw "~y,steel);
  var hw=cyl(context,id+("homePcbWasher"~y),vector(-34.00001,y,length-2),vector(1,0,0),2.5,0.5);
  cut(context,id+("homePcbWasherBore"~y),hw,cyl(context,id+("homePcbWasherTool"~y),vector(-34.10001,y,length-2),vector(1,0,0),1.35,0.7));
  namePart(context,hw,"REF Home M2.5 PCB washer 5 x 2.7 x 0.5 "~y,steel);
 }
 for(var h in [length-11,length-3]){
 }


 }
 stage="raised guide system datum";
 var stationary=[xCarrier];
 for(var joint in [[-36,16],[-36,96],[36,16],[36,96]])stationary=append(stationary,qCreatedBy(id+("xJointScrew"~joint[0]~joint[1]),EntityType.BODY));
 opTransform(context,id+"guideSystemLift",{"bodies":qSubtraction(qBodyType(qEverything(EntityType.BODY),BodyType.SOLID),qUnion(stationary)),"transform":transform(vector(0,0,guideLift)*millimeter)});

 stage="printed rear X plate";
 var rearInst=newInstantiator(id+"rearPlateSource");
 addInstance(rearInst,OriginalX::build,{"partQuery":qCompressed(1.0,"%B5$QueryM5Sa$entityTypeBa$EntityTypeS4$BODYSb$historyTypeS8$CREATIONS9$importTagD48613Sb$operationIdB2$IdA1Sf.8$FFopYUoW9RDPWMSimportOpS9$queryTypeS6$IMPORT",newId()),"name":"originalRear"});
 instantiate(context,rearInst);
 var rearPlate=qBodyType(qCreatedBy(id+"rearPlateSource",EntityType.BODY),BodyType.SOLID);
 if(size(evaluateQuery(context,rearPlate))!=1)throw regenError("Expected one original rear X plate");
 opTransform(context,id+"rearPlateDatum",{"bodies":rearPlate,"transform":transform(matrix([[1, -3.02618534525674e-16, -1.2246467991378198e-16], [-1.2246467991378198e-16, 3.7999999999975497e-16, -1], [3.02618534525674e-16, 1, 3.7999999999975497e-16]]),vector(965.2805780454711,-22.999998897315233,189.59393165141555)*millimeter)});
 cut(context,id+"rearMotorClearLeft",rearPlate,rect(context,id+"rearMotorClearLeftTool",-100,-40,-20,-14,-20,3.5));
 cut(context,id+"rearMotorClearRight",rearPlate,rect(context,id+"rearMotorClearRightTool",14,-40,-20,100,-20,3.5));
 namePart(context,rearPlate,"11 X Rear Plate R16",color(0.62,0.61,0.57));
 }catch(error){throw regenError(stage~": "~error);}
});
