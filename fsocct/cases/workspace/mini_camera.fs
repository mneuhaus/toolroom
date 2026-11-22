FeatureScript 3070;
import(path : "onshape/std/common.fs", version : "3070.0");

// Mini R3: integrated flat A1 Mini functional model. One lifting step, 130 mm stroke,
// 120 mm lifting plate, 100 mm active pickup width. Local X width, Y away from wall, Z motion.
// The 300 mm MGN12H rails are purchased hardware and remain full length.
// R3: 18 mm moving rail seats; 150 mm open feet; drive at X=-22/Y=28.
const POS = { (millimeter) : [0, 0, 130] } as LengthBoundSpec;
const EDGE = { (millimeter) : [3.2, 4.8, 6] } as LengthBoundSpec;
const GAP = { (millimeter) : [0.2, 0.5, 0.7] } as LengthBoundSpec;
const TILT = { (degree) : [60, 65, 70] } as AngleBoundSpec;
const TENSION = { (millimeter) : [-3, 0, 3] } as LengthBoundSpec;
const GREY = color(0.29,0.34,0.38);
const PALE = color(0.77,0.82,0.83);
const ORANGE = color(0.98,0.47,0.12);
const STEEL = color(0.65,0.68,0.71);
const DARK = color(0.12,0.14,0.16);

function body(id is Id) returns Query
{ return qBodyType(qCreatedBy(id,EntityType.BODY),BodyType.SOLID); }
function prism(context is Context,id is Id,pl is Plane,pts is array,dir is Vector,d) returns Query
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":pl});
 for(var i=0;i<size(pts);i+=1)skLineSegment(sk,"e"~i,{"start":vector(pts[i][0],pts[i][1])*millimeter,"end":vector(pts[(i+1)%size(pts)][0],pts[(i+1)%size(pts)][1])*millimeter});
 skSolve(sk);opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":dir,"endBound":BoundingType.BLIND,"endDepth":d*millimeter});
 opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});return body(id);
}
function rect(context is Context,id is Id,x0,y0,z0,x1,y1,z1) returns Query
{return prism(context,id,plane(vector(0,y0,0)*millimeter,vector(0,-1,0),vector(1,0,0)),[[x0,z0],[x1,z0],[x1,z1],[x0,z1]],vector(0,1,0),y1-y0);}
function yz(context is Context,id is Id,x0,pts is array,t) returns Query
{return prism(context,id,plane(vector(x0,0,0)*millimeter,vector(1,0,0),vector(0,1,0)),pts,vector(1,0,0),t);}
function cyl(context is Context,id is Id,p is Vector,axis is Vector,r,h) returns Query
{
 var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(p*millimeter,axis)});
 skCircle(sk,"c",{"center":vector(0,0)*millimeter,"radius":r*millimeter});skSolve(sk);
 opExtrude(context,id,{"entities":qSketchRegion(id+"sk"),"direction":axis,"endBound":BoundingType.BLIND,"endDepth":h*millimeter});
 opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});return body(id);
}
function cut(context is Context,id is Id,a is Query,b is Query)
{opBoolean(context,id,{"targets":a,"tools":b,"operationType":BooleanOperationType.SUBTRACTION});}
function join(context is Context,id is Id,a is Query,b is Query)
{opBoolean(context,id,{"tools":qUnion([a,b]),"operationType":BooleanOperationType.UNION});}
function bore(context is Context,id is Id,q is Query,p is Vector,axis is Vector,r,h)
{cut(context,id+"cut",q,cyl(context,id,p,axis,r,h));}
function finish(context is Context,q is Query,n is string,c is Color)
{
 if(size(evaluateQuery(context,q))!=1)throw regenError("Expected one connected part: "~n);
 setProperty(context,{"entities":q,"propertyType":PropertyType.NAME,"value":n});
 setProperty(context,{"entities":q,"propertyType":PropertyType.APPEARANCE,"value":c});
}
function corners(context is Context,id is Id,q is Query,axis,r)
{
 var es=[];for(var e in evaluateQuery(context,qGeometry(qOwnedByBody(q,EntityType.EDGE),GeometryType.LINE))){var ln=evLine(context,{"edge":e});if(abs(ln.direction[axis])>0.999)es=append(es,e);}
 if(size(es)>0)opFillet(context,id,{"entities":qUnion(es),"radius":r*millimeter});
}
function fastener(context is Context,id is Id,p is Vector,axis is Vector,d,len) returns Query
{
 var q=cyl(context,id+"shank",p,axis,d/2,len);
 join(context,id+"join",q,cyl(context,id+"head",p-axis*d,axis,d==2?1.9:(d==2.5?2.25:(d==3?2.75:4.25)),d));
 bore(context,id+"socket",q,p-axis*(d+0.01),axis,d==2?0.8:(d==2.5?1:(d==3?1.25:2)),1.5);
 return q;
}
function pilot(context is Context,id is Id,q is Query,p is Vector,axis is Vector,h)
{bore(context,id,q,p,axis,1.3,h);}


function armKey(context is Context,id is Id,c is number,y0,y1) returns Query
{return prism(context,id,plane(vector(0,y0,0)*millimeter,vector(0,-1,0),vector(1,0,0)),[[94-c,36-c],[106+c,36-c],[110+c,50+c],[90-c,50+c]],vector(0,1,0),y1-y0);}
function bar(context is Context,id is Id,a is Vector,b is Vector) returns Query
{
 var delta=b-a;
 return prism(context,id,plane(a*millimeter,normalize(delta),normalize(cross(vector(0,0,1),delta))),[[-9,-8],[9,-8],[9,8],[-9,8]],normalize(delta),norm(delta));
}
annotation {"Feature Type Name":"Single step MINI camera add-on R4"}
export const miniCameraR4=defineFeature(function(context is Context,id is Id,definition is map)
precondition{}
{
 // Split saddle on stationary right core, below hopper and MGN12H carriage.
 var saddle=rect(context,id+"saddle",48,16,-43,88,27,-22);
 cut(context,id+"saddleSeat",saddle,rect(context,id+"seat",57.7,19,-43.1,78.3,27.1,-16.9));
 var cap=rect(context,id+"cap",48,29,-43,88,34,-22);
 for(var x in [52,84]){
  pilot(context,id+("clampPilot"~x),saddle,vector(x,17,-32),vector(0,1,0),10.1);
  bore(context,id+("clampClear"~x),cap,vector(x,28.9,-32),vector(0,1,0),1.7,5.2);
 }
 // Triangulated side arm outside the entire moving rail envelope.
 var arm=yz(context,id+"arm",88,[[-96,36],[-96,52],[-78,52],[26,-19],[26,-36],[14,-36]],12);
 join(context,id+"armSaddle",saddle,rect(context,id+"armRoot",82,16,-36,94,26,-22));join(context,id+"armJoin",saddle,arm);
 join(context,id+"tongueJoin",saddle,armKey(context,id+"tongue",0,-118,-94));
 pilot(context,id+"jointPilot",saddle,vector(99,-105,43),vector(1,0,0),12);
 // Socket beam and adapter ring sit behind the existing camera shell.
 var outer=rect(context,id+"outer",85,-123,31,115,-96.2,55);
 cut(context,id+"socketCut",outer,armKey(context,id+"socket",0.2,-118.2,-96.1));
 bore(context,id+"jointClear",outer,vector(109.4,-105,43),vector(1,0,0),1.7,5.7);
 // Horizontal diagonal cross-arm, 16 mm deep. All beam points are behind the optic.
 var boom=bar(context,id+"boom",vector(100,-112,45),vector(43,-276,176));
 join(context,id+"boomJoin",outer,boom);
 var ring=rect(context,id+"ring",-32,-277.2,13,48,-272.2,77);
 bore(context,id+"lensWindow",ring,vector(0,-277.3,45),vector(0,1,0),26.2,5.2);
 for(var x in [-25,25])bore(context,id+("cameraClear"~x),ring,vector(x,-277.3,45-x),vector(0,1,0),1.7,5.2);
 var opticalPose=transform(vector(0,0,115)*millimeter)*rotationAround(line(vector(0,-240,45)*millimeter,vector(1,0,0)),-23.6293777307*degree);
 opTransform(context,id+"raiseOptics",{"bodies":ring,"transform":opticalPose});
 join(context,id+"ringJoin",outer,ring);
 // Clear the tongue after joining the beam, so it cannot refill the socket.
 cut(context,id+"socketFinal",outer,armKey(context,id+"socketFinalTool",0.2,-118.2,-96.1));
 // Final bores after the arm-root union, which crosses the right saddle pilot.
 for(var x in [52,84])pilot(context,id+("clampPilotFinal"~x),saddle,vector(x,17,-32),vector(0,1,0),10.1);
 // Raised front housing datum (0,-240,160), aimed at local (0,0,55).
 finish(context,saddle,"P30 Camera side arm and core saddle R4",GREY);
 finish(context,cap,"P31 Camera saddle cap R4",GREY);
 finish(context,outer,"P32 Camera boom and Obsbot interface R4",GREY);
 var pose=transform(vector(0,0,260)*millimeter)*rotationAround(line(vector(0,0,0)*millimeter,vector(1,0,0)),-25*degree);
 opTransform(context,id+"world",{"bodies":qUnion([saddle,cap,outer]),"transform":pose});
});
