FeatureScript 2892;
import(path : "onshape/std/common.fs", version : "2892.0");
function fillSection(context is Context,id is Id,x is number,r is number,floorN is number) returns Query
{
 var k=1.0344073449972673;var sn=sqrt(1+k*k);
 var originS=(floorN+0.3*sn)/k;var c=r*(1+sn)/k;
 var ts=(c+k*r)/(1+k*k);var tn=k*ts;
 var endS=c-sqrt(2*r-1);var centre=vector(originS+c,floorN+r);
 var a0=atan2(1-r,endS-c);var a1=atan2(tn-r,ts-c)-360*degree;
 var am=(a0+a1)/2;var mid=centre+r*vector(cos(am),sin(am));
 var o=vector(originS,floorN);var b=vector(originS+endS,floorN);
 var f=vector(originS+endS,floorN+1);var t=vector(originS+ts,floorN+tn);
 var sk=newSketchOnPlane(context,id,{"sketchPlane":plane(vector(x,0,0)*millimeter,vector(1,0,0),vector(0,1,0))});
 skLineSegment(sk,"bottom",{"start":o*millimeter,"end":b*millimeter});
 skLineSegment(sk,"blunt",{"start":b*millimeter,"end":f*millimeter});
 skArc(sk,"chute",{"start":f*millimeter,"mid":mid*millimeter,"end":t*millimeter});
 skLineSegment(sk,"rear",{"start":t*millimeter,"end":o*millimeter});
 skSolve(sk);return qSketchRegion(id,false);
}
function trimOutside(context is Context,id is Id,body is Query,normal is Vector,point is Vector)
{
 var sk=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(point*millimeter,normal)});
 skRectangle(sk,"rect",{"firstCorner":vector(-500,-500)*millimeter,"secondCorner":vector(500,500)*millimeter});skSolve(sk);
 opExtrude(context,id+"ex",{"entities":qSketchRegion(id+"s",false),"direction":normal,"endBound":BoundingType.BLIND,"endDepth":500*millimeter});
 opBoolean(context,id+"cut",{"tools":qCreatedBy(id+"ex",EntityType.BODY),"targets":body,"operationType":BooleanOperationType.SUBTRACTION});
 opDeleteBodies(context,id+"d",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
}
annotation {"Feature Type Name":"Belt hopper rounded corner inserts R1"}
export const cornerInsertsR1=defineFeature(function(context is Context,id is Id,definition is map)
precondition{}
{
 var sections=[];var sketches=[];
 for(var x in [-120,-95,-72,-51,-44,-36.5]){
  var n=x<=-51?0.3:0.3-(x+51)/14.5*12.3;
  var r=18+0.55*(-x-36.5);var sid=id+("section"~x);
  sections=append(sections,fillSection(context,sid,x,r,n));sketches=append(sketches,qCreatedBy(sid,EntityType.BODY));
 }
 opLoft(context,id+"loft",{"profileSubqueries":sections});var left=qCreatedBy(id+"loft",EntityType.BODY);
 opDeleteBodies(context,id+"sketches",{"entities":qUnion(sketches)});
 var n=normalize(vector(-0.6932337712483952,-0.6241555926213797,-0.360356399416164));
 trimOutside(context,id+"side",left,n,vector(-51,0,0)-n*0.3);
 // Exact main-panel seat: remove interpolation overshoot only outside belt.
 var sk=newSketchOnPlane(context,id+"floorSk",{"sketchPlane":plane(vector(0,0,0.3)*millimeter,vector(0,0,1),vector(1,0,0))});
 skRectangle(sk,"seat",{"firstCorner":vector(-300,-100)*millimeter,"secondCorner":vector(-51,300)*millimeter});skSolve(sk);
 opExtrude(context,id+"floorTool",{"entities":qSketchRegion(id+"floorSk",false),"direction":vector(0,0,-1),"endBound":BoundingType.BLIND,"endDepth":100*millimeter});
 opBoolean(context,id+"floorCut",{"targets":left,"tools":qCreatedBy(id+"floorTool",EntityType.BODY),"operationType":BooleanOperationType.SUBTRACTION});
 opDeleteBodies(context,id+"floorDel",{"entities":qCreatedBy(id+"floorSk",EntityType.BODY)});
 opPattern(context,id+"mirror",{"entities":left,"transforms":[mirrorAcross(plane(vector(0,0,0)*millimeter,vector(1,0,0)))],"instanceNames":["right"]});var right=qCreatedBy(id+"mirror",EntityType.BODY);
 setProperty(context,{"entities":left,"propertyType":PropertyType.NAME,"value":"P01 Hopper rounded corner L R1 - glue in"});
 setProperty(context,{"entities":right,"propertyType":PropertyType.NAME,"value":"P02 Hopper rounded corner R R1 - glue in"});
 setProperty(context,{"entities":qUnion([left,right]),"propertyType":PropertyType.APPEARANCE,"value":color(0.28,0.64,0.53)});
 var tr=transform(matrix([[1,0,0],[0,0.5,-0.8660254037844386],[0,0.8660254037844386,0.5]]),vector(77.1263837814323,-498.4724643754777,-184.5128995194368)*millimeter);
 opTransform(context,id+"pose",{"bodies":qUnion([left,right]),"transform":tr});
});
