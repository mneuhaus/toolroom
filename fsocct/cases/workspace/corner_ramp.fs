FeatureScript 2892;
import(path : "onshape/std/common.fs", version : "2892.0");
function polygon(context is Context,id is Id,pl is Plane,pts is array) returns Query
{
 var sk=newSketchOnPlane(context,id,{"sketchPlane":pl});
 for(var i=0;i<size(pts);i+=1)skLineSegment(sk,"edge"~i,{"start":vector(pts[i][0],pts[i][1])*millimeter,"end":vector(pts[(i+1)%size(pts)][0],pts[(i+1)%size(pts)][1])*millimeter});
 skSolve(sk);return qSketchRegion(id,false);
}
function prism(context is Context,id is Id,pl is Plane,pts is array,dir is Vector,d is number) returns Query
{
 var q=polygon(context,id+"sk",pl,pts);
 opExtrude(context,id,{"entities":q,"direction":dir,"endBound":BoundingType.BLIND,"endDepth":d*millimeter});
 opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});return qCreatedBy(id+"ex",EntityType.BODY);
}
function finish(context is Context,q is Query,n is string)
{
 setProperty(context,{"entities":q,"propertyType":PropertyType.NAME,"value":n});
 setProperty(context,{"entities":q,"propertyType":PropertyType.APPEARANCE,"value":color(0.20,0.62,0.48)});
}
annotation {"Feature Type Name":"Belt hopper continuous side shields R3"}
export const cornerInsertsR3=defineFeature(function(context is Context,id is Id,definition is map)
precondition{}
{
 var q0=vector(77.1263837814323,-498.4724643754777,-184.5128995194368);
 var uphill=vector(0,0.5,0.8660254037844386);var xAxis=vector(1,0,0);
 // [X,-N]. This closed section is a thin, solid ramp, with no basin below.
 // It begins before the belt entry and ends 1.2 mm outside the cleat span.
 var leftPts=[[-36.3,10.0],[-50.7,0.3],[-50.7,2.3],[-49.7,3.0],[-36.3,12.4]];
 var rightPts=[[36.3,10.0],[50.7,0.3],[50.7,2.3],[49.7,3.0],[36.3,12.4]];
 var left=prism(context,id+"left",plane(q0+uphill*(-3)*millimeter,uphill,xAxis),leftPts,uphill,103.0);
 var right=prism(context,id+"right",plane(q0+uphill*(-3)*millimeter,uphill,xAxis),rightPts,uphill,103.0);
 finish(context,left,"P01 Hopper corner ramp and side shield L R3");
 finish(context,right,"P02 Hopper corner ramp and side shield R R3");
});
