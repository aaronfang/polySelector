import maya.OpenMaya as om
import maya.cmds as cmds
import math
import os
from operator import itemgetter, attrgetter, methodcaller

class polySelector:

#----------------------------------------------------------------------------------------------------------------------
	def __init__(self):
		self.targetGeom = []
		self.geometryData = GeometryData()
		self.geometryData.setPolyData()



	def printMMatrix(matrix):
		endStr = '\n'
		outStr = ''
		outStr += endStr

		for r in range(0,4):
			for c in range(0,4):
				outStr += str(matrix(r,c)) + str(' ')
			outStr += endStr

		print 'transformation: ',  outStr




	def select(self):

		#set_polyData()
		targetIds = []
		poly_ids = []

		targetIds = self.getCornerPolygonIds()
		poly_ids = self.geometryData.surround_building(targetIds)
		poly_ids = self.geometryData.selectPolygons(poly_ids)

		sel = om.MSelectionList()
		om.MGlobal.getActiveSelectionList(sel)

		mdag = om.MDagPath()
		sel.getDagPath(0, mdag)

		print "poly_ids: ",  poly_ids[0]

		# Create an MIntArray and populate it with component ids to add to our component object
		# MIntArray takes an array of ints. That has to be passed using an MScriptUtil pointer
		# This is where you would use your list of polyIds that you had gotten
		#poly_ids = [faceIndex]
		util = om.MScriptUtil()
		util.createFromList(poly_ids, len(poly_ids))
		ids_ptr = util.asIntPtr()
		polyids = om.MIntArray(ids_ptr, len(poly_ids))

		# Create a singleIndexedComponent of type polygon
		mfn_components = om.MFnSingleIndexedComponent()
		components = mfn_components.create(om.MFn.kMeshPolygonComponent)
		# Add our MIntArray of ids to the component
		mfn_components.addElements(polyids)

		to_sel = om.MSelectionList()
		# The object the selection refers to, and the components on that object to select
		to_sel.add(mdag, components)
		om.MGlobal.setActiveSelectionList(to_sel)

		#return getDirectionalFace(faceIndex, om.MVector(0,1,0))




	def getCornerPolygonIds(self):
		targetGeom = []

		selList = om.MSelectionList()
		#lägger till markerade meshar i listan selList
		om.MGlobal.getActiveSelectionList(selList)

		# om inget polygon är markerat
		if selList.isEmpty():
			print "Select four polygons"
			return


		# itererar igenom objektets noder, de noder som finns i hypergraphen
		selListIter = om.MItSelectionList(selList)
		while not selListIter.isDone():
			print "selListIter"

			components = om.MObject()
			dagPath = om.MDagPath()
			selListIter.getDagPath(dagPath, components)

			if components.isNull():   
				selListIter.next()
				continue

			compListFn = om.MFnComponent(components)
			compType = compListFn.componentType()

			if compType == om.MFn.kMeshVertComponent:
				# allows compListFn to query single indexed components
				compListFn = om.MFnSingleIndexedComponent(components)
				targetIds = om.MIntArray()
				# äntligen får vi ut samtliga id för de markerade polygonen
				compListFn.getElements(targetIds)


			# kontrollerar om det finns ett polygon i komponenterna 
			if compType == om.MFn.kMeshPolygonComponent:
				# allows compListFn to query single indexed components
				compListFn = om.MFnSingleIndexedComponent(components)
				targetIds = om.MIntArray()
				# äntligen får vi ut samtliga id för de markerade polygonen
				compListFn.getElements(targetIds)

			selListIter.next()

		if len(targetIds) > 10:
			print "too many polygons selected"
			return

		return targetIds

	

#######################################################################################################################

class GeometryData:

#----------------------------------------------------------------------------------------------------------------------
	def __init__(self):
		
		self.polygons = []
		self.edges = []
		self.vertex = []

	def printMatrix(self,matrix):
		endStr = '\n'
		outStr = ''
		outStr += endStr

		for i in range(0,16):
			if i == 0:
				outStr += '['

			if( i > 0 and i%4==0):
				outStr += endStr
			outStr += str(matrix[i]) + str(' ')
		outStr += ']'

		print 'transformation: ',  outStr

	def setPolyData(self):
		print "tja"
		selList = om.MSelectionList()
		#lägger till markerade meshar i listan selList
		om.MGlobal.getActiveSelectionList(selList)

		print "selList length", selList
		if selList.isEmpty():
			print "No polygon is selected"
			return


		components = om.MObject()
		dagPath = om.MDagPath()
		selList.getDagPath(0, dagPath, components)

		# hämtar namnet på huvud noden
		pathName = dagPath.fullPathName()
		subName = pathName[(pathName.find("|")+1):len(pathName)]
		meshName = subName[0:(subName.find("|"))]

		print "dagPath: ",meshName 




		#transformations matris, skala, rotation och translatering
		meshMatrix = cmds.xform(meshName, q=True, ws=True, matrix=True)
		#plockar ut andra kolumnen med 3 componenter, kommer motsvara en vektor som pekar i Y-riktning eftersom vi drar nytta av skalningen som 'alltid' är positiv
		#vi kunde lika gärna gjort en egen vektor (0,1,0) istället för (0,y-skalning,0)

		self.printMatrix(meshMatrix)

		transMatrix = om.MMatrix()
		om.MScriptUtil.createMatrixFromList(meshMatrix, transMatrix) 

		#printMatrix(meshMatrix)

		primaryUp = om.MVector(*meshMatrix[4:7])
		#polockar ut andra raden
		# have a secondary up vector for faces that are facing the same way as the original up
		# pekar i z-riktning
		secondaryUp = om.MVector(*meshMatrix[8:11])


		connectedFaces = om.MIntArray()
		
		faceIndecis = om.MIntArray()
		polyEdgesIds = om.MIntArray()
		dummy = om.MScriptUtil()
		edgeFaces = om.MIntArray()
		dummyIntPtr = dummy.asIntPtr()
		self.polyData = []
		 #MStatus status
		# targetGeom är den markerade meshen

		edgeIter = om.MItMeshEdge(dagPath)
		vertexIter = om.MItMeshVertex(dagPath)
		faceIter = om.MItMeshPolygon(dagPath)

		self.vertex = [VertexData() for _ in xrange(vertexIter.count())]

		print "vertexIter.count()", vertexIter.count()

		i=0
		while not vertexIter.isDone():

			connectedFaces = om.MIntArray()
			vertexIter.getConnectedFaces(connectedFaces)

			self.vertex[i].connectedFaces = connectedFaces

			connectedVertices = om.MIntArray()
			vertexIter.getConnectedVertices(connectedVertices)

			self.vertex[i].connectedVertices = connectedVertices

			self.vertex[i].position = vertexIter.position()
			self.vertex[i].numberOfNeighbors = len(connectedVertices)
			i+=1
			vertexIter.next()



		# self.edges = [EdgeData() for _ in xrange(edgeIter.count())]
		# while not edgeIter.isDone():

		# 	connectedEdges = om.MIntArray()
  #           edgeIter.getConnectedEdges(connectedEdges)

  #           self.edges[i].connectedEdges = connectedEdges

  #           self.edges[i].edgePosition = edgeIter.center()
  #           self.edges[i].numberOfNeighbors = edgeIter.numConnectedEdges()
  #           i+=1
  #           edgeIter.next()

		# #initierar faceIter.count() antal toma polygons till objektet
		self.polygons = [PolyData() for _ in xrange(faceIter.count())]


		#print "edgeIter: " + str(edgeIter.index())
		# här loopar vi igenom alla faces i meshen
		i=0
		while not faceIter.isDone():
			#print "index: ", faceIter.index()
			#cfLength = edgeIter.getConnectedFaces(connectedFaces)
			polyData = self.polygons[i]
			self.polygons[i].normalAngel = 5.0


			self.polygons[i].position = faceIter.center()

			normal = om.MVector()
			faceIter.getNormal(normal)
			self.polygons[i].normal = normal

			#hittar de tre anslutande polygonen
			faceArray = om.MIntArray()
			faceIter.getConnectedFaces(faceArray)

			vertexArray = om.MIntArray()
			faceIter.getVertices(vertexArray)

			self.polygons[i].vertices = vertexArray

			#lägger till de tre anslutande polygonen i faceNeighbors listan
			self.polygons[i].connectedFaces = faceArray


			i+=1
			faceIter.next()

	def surround_building(self,targetIds):

		neighborFaces = []
		selectedFaces = []


		# poly_selectedList=[{'id':targetIds[0], 'x':self.polygons[targetIds[0]].polyPosition.x, 'z':self.polygons[targetIds[0]].polyPosition.y },
		# 				   {'id':targetIds[1], 'x':self.polygons[targetIds[1]].polyPosition.x, 'z':self.polygons[targetIds[1]].polyPosition.y },
		# 				   {'id':targetIds[2], 'x':self.polygons[targetIds[2]].polyPosition.x, 'z':self.polygons[targetIds[2]].polyPosition.y },
		# 				   {'id':targetIds[3], 'x':self.polygons[targetIds[3]].polyPosition.x, 'z':self.polygons[targetIds[3]].polyPosition.y }]

		poly_selectedList=[{'id':targetIds[0], 'x':self.vertex[targetIds[0]].position.x, 'z':self.vertex[targetIds[0]].position.z },
						   {'id':targetIds[1], 'x':self.vertex[targetIds[1]].position.x, 'z':self.vertex[targetIds[1]].position.z },
						   {'id':targetIds[2], 'x':self.vertex[targetIds[2]].position.x, 'z':self.vertex[targetIds[2]].position.z },
						   {'id':targetIds[3], 'x':self.vertex[targetIds[3]].position.x, 'z':self.vertex[targetIds[3]].position.z }]
		
		#sorted(poly_selectedList, key=lambda k: k['x'])

		poly_selectedList.sort(key=lambda x: (-x['x'],x['z']))

		startIndex = poly_selectedList[0]["id"]
		secondIndex = poly_selectedList[1]["id"]
		thirdIndex = poly_selectedList[3]["id"]
		fourthIndex = poly_selectedList[2]["id"]

		print "startIndex", startIndex
		print "secondIndex", secondIndex
		print "thirdIndex", thirdIndex
		print "fourthIndex", fourthIndex

		#lägger till det först markeade facet
		selectedFaces.append(startIndex)

		print "negativ z-sträcka"
		axis = 'z'
		index = 0

		currentIndex = self.getDirectionalFace(selectedFaces[index], axis, secondIndex, -1)
		while currentIndex != secondIndex:
			if os.path.exists("c:/break"): break
			if currentIndex == secondIndex:
				print "found"
			selectedFaces.append(currentIndex)
			index += 1
			currentIndex = self.getDirectionalFace(selectedFaces[index], axis, secondIndex, selectedFaces[-2])
			
			
		
		# print "negativ x-sträcka"
		selectedFaces.append(secondIndex)
		axis = 'x'
		index += 1
		currentIndex = self.getDirectionalFace(selectedFaces[index], axis, thirdIndex, selectedFaces[-2])
		while currentIndex != thirdIndex:
			if os.path.exists("c:/break"): break
			if currentIndex == thirdIndex:
				print "found"
			selectedFaces.append(currentIndex)
			index += 1
			currentIndex = self.getDirectionalFace(selectedFaces[index], axis, thirdIndex, selectedFaces[-2])
			
			
			
			
		
		# print "positiv z-sträcka"
		selectedFaces.append(thirdIndex)
		axis = 'z'
		index += 1
		currentIndex = self.getDirectionalFace(selectedFaces[index], axis, fourthIndex, selectedFaces[-2])
		while currentIndex != fourthIndex:
			if os.path.exists("c:/break"): break
			if currentIndex == fourthIndex:
				print "found" 
			selectedFaces.append(currentIndex)
			index += 1
			currentIndex = self.getDirectionalFace(selectedFaces[index], axis, fourthIndex, selectedFaces[-2])
			

		# print "positiv x-sträcka"
		selectedFaces.append(fourthIndex)
		axis = 'x'
		index += 1
		currentIndex = self.getDirectionalFace(selectedFaces[index], axis, startIndex,selectedFaces[-2])
		while currentIndex != startIndex:
			if os.path.exists("c:/break"): break
			if currentIndex == startIndex:
				print "found"
			selectedFaces.append(currentIndex)
			index += 1
			currentIndex = self.getDirectionalFace(selectedFaces[index], axis, startIndex,selectedFaces[-2])
			
			

		return selectedFaces

	def getDirectionalFace(self, selectedFaces, axis, endIndex, lastIndex):

		# startFaceMatrix = self.polygons[selectedFaces].faceMatrix
		# endFaceMatrix = self.polygons[endIndex].faceMatrix

		# nMatrix = endFaceMatrix * startFaceMatrix.inverse()
		# nVector = om.MVector(nMatrix(3,0), nMatrix(3,1), nMatrix(3,2))

		nextFace = -1

		goalPos= self.vertex[endIndex].position
		currentPos= self.vertex[selectedFaces].position



		CG = goalPos - currentPos

		goalMagnitude = math.sqrt(math.pow(CG.x,2)+math.pow(CG.y,2)+math.pow(CG.z,2))


		goalPosProduct = self.dotProduct(CG,currentPos)

		if goalMagnitude == 0.0:
			return endIndex


		selectedVertexNeighbors = self.vertex[selectedFaces].connectedVertices

		closestAngel = 100

		foundCandidate = False


		for i in range(0,len(selectedVertexNeighbors)):
			neighborPos = self.vertex[selectedVertexNeighbors[i]].position

			CN = neighborPos - currentPos

			neighborMagnitude = math.sqrt(math.pow(CN.x,2)+math.pow(CN.y,2)+math.pow(CN.z,2))

			if neighborMagnitude == 0:

				foundIndex = i
				break

			
			neighborPosProduct = self.dotProduct(CG,CN)
			neighborAngel = math.acos((neighborPosProduct/(goalMagnitude*neighborMagnitude+0.00001)))

			neighborAngel = neighborAngel*(180/3.1416)

			if neighborAngel < closestAngel and self.vertex[selectedVertexNeighbors[i]].selected != True:

				foundIndex = i
				foundCandidate = True
				closestAngel = neighborAngel

		closestDistance = -1

		#method 2
		closestDistance = math.sqrt(math.pow(goalPos.x-currentPos.x,2)+math.pow(neighborPos.y-currentPos.y,2)+math.pow(neighborPos.y-currentPos.z,2))
		if foundCandidate == False:
			print "method 2"
			for i in range(0,len(selectedVertexNeighbors)):
				neighborPos = self.vertex[selectedVertexNeighbors[i]].position
				neighborToGoal = math.sqrt(math.pow(goalPos.x-neighborPos.x,2)+math.pow(neighborPos.y-neighborPos.y,2)+math.pow(neighborPos.y-neighborPos.z,2))

				if neighborToGoal < closestDistance and self.vertex[i].selected != True:
					foundIndex = i
					closestDistance = neighborToGoal


		nextVertex = selectedVertexNeighbors[foundIndex]

		self.vertex[nextVertex].selected = True


		print "nextVertex", nextVertex

		# selectedFaceNeighbors = self.polygons[selectedFaces].connectedFaces
		

		# numberOfNeighbors = len(selectedFaceNeighbors)


		# if numberOfNeighbors == 3:
		# 	# omskrivning till ngt kortare
		# 	neighborsPos0 = self.polygons[selectedFaceNeighbors[0]].polyPosition
		# 	neighborsPos1 = self.polygons[selectedFaceNeighbors[1]].polyPosition
		# 	neighborsPos2 = self.polygons[selectedFaceNeighbors[2]].polyPosition

		# 	distance1_3D = math.sqrt(math.pow(goalPos.x-neighborsPos0.x,2)+math.pow(goalPos.y-neighborsPos0.y,2))
		# 	distance2_3D = math.sqrt(math.pow(goalPos.x-neighborsPos1.x,2)+math.pow(goalPos.y-neighborsPos1.y,2))
		# 	distance3_3D = math.sqrt(math.pow(goalPos.x-neighborsPos2.x,2)+math.pow(goalPos.y-neighborsPos2.y,2))

		# 	#distance1_2D = math.sqrt(math.pow(goalPos.x-polyPosition[selectedFaceNeighbors[0]].x,2)+math.pow(goalPos.y-polyPosition[selectedFaceNeighbors[0]].y,2))
		# 	#distance2_2D = math.sqrt(math.pow(goalPos.x-polyPosition[selectedFaceNeighbors[1]].x,2)+math.pow(goalPos.y-polyPosition[selectedFaceNeighbors[1]].y,2))
		# 	#distance3_2D = math.sqrt(math.pow(goalPos.x-polyPosition[selectedFaceNeighbors[2]].x,2)+math.pow(goalPos.y-polyPosition[selectedFaceNeighbors[2]].y,2))
		# elif numberOfNeighbors == 2:
		# 	neighborsPos0 = self.polygons[selectedFaceNeighbors[0]].polyPosition
		# 	neighborsPos1 = self.polygons[selectedFaceNeighbors[1]].polyPosition

		# 	distance1_3D = math.sqrt(math.pow(goalPos.x-neighborsPos0.x,2)+math.pow(goalPos.y-neighborsPos0.y,2)+math.pow(goalPos.z-neighborsPos0.z,2))
		# 	distance2_3D = math.sqrt(math.pow(goalPos.x-neighborsPos1.x,2)+math.pow(goalPos.y-neighborsPos1.y,2)+math.pow(goalPos.z-neighborsPos1.z,2))
			
		# 	# något som är större än distance1 och distance2
		# 	distance3_3D = distance1_3D+distance2_3D

		# elif numberOfNeighbors == 1:
		# 	print "one neighbors"
		# 	distance1_3D = abs(goalPos-neighborsPos0,str(axis))
		# 	# något som är större än distance1
		# 	distance2_3D = distance1+distance1_3D
		# 	distance3_3D = distance1+distance1_3D


		# if numberOfNeighbors == 3:
		# 	if distance1_3D<distance2_3D and distance1_3D<distance3_3D:
		# 		nextFace = selectedFaceNeighbors[0]
		# 	elif distance2_3D<distance3_3D and distance2_3D<distance1_3D:
		# 		nextFace = selectedFaceNeighbors[1]
		# 	elif distance3_3D<distance1_3D and distance3_3D<distance2_3D:
		# 		nextFace = selectedFaceNeighbors[2]

		# elif numberOfNeighbors == 2:
		# 	if distance1_3D<distance2_3D:
		# 		nextFace = selectedFaceNeighbors[0]
		# 	else:
		# 		nextFace = selectedFaceNeighbors[1]



		# if numberOfNeighbors == 3:
		# 	if nextFace == selectedFaceNeighbors[0] and self.polygons[selectedFaceNeighbors[0]].selected == True:
		# 		print "case1"
		# 		if distance2_3D<distance3_3D and self.polygons[selectedFaceNeighbors[1]].selected != True: 
		# 			nextFace = selectedFaceNeighbors[1]
		# 		elif self.polygons[selectedFaceNeighbors[2]].selected != True:
		# 			nextFace = selectedFaceNeighbors[2]
		# 		else:
		# 			print "no solution"

		# 	elif nextFace == selectedFaceNeighbors[1] and self.polygons[selectedFaceNeighbors[1]].selected == True:
		# 		print "case2"
		# 		if distance1_3D<distance3_3D and self.polygons[selectedFaceNeighbors[0]].selected != True: 
		# 			nextFace = selectedFaceNeighbors[0]
		# 		elif self.polygons[selectedFaceNeighbors[2]].selected != True:
		# 			nextFace = selectedFaceNeighbors[2]
		# 		else:
		# 			print "no solution"

		# 	elif nextFace == selectedFaceNeighbors[2] and self.polygons[selectedFaceNeighbors[2]].selected == True:
		# 		print "case3"
		# 		if distance1_3D<distance2_3D and self.polygons[selectedFaceNeighbors[0]].selected != True: 
		# 			nextFace = selectedFaceNeighbors[0]
		# 		elif self.polygons[selectedFaceNeighbors[1]].selected != True:
		# 			nextFace = selectedFaceNeighbors[1]
		# 		else:
		# 			print "no solution"

		# elif numberOfNeighbors == 2:
		# 	if nextFace == selectedFaceNeighbors[0] and self.polygons[selectedFaceNeighbors[0]].selected == True:
		# 		print "case4"
		# 		if self.polygons[selectedFaceNeighbors[1]].selected != True:
		# 			nextFace = selectedFaceNeighbors[1]
		# 	elif nextFace == selectedFaceNeighbors[1] and self.polygons[selectedFaceNeighbors[1]].selected == True:
		# 		print "case5"
		# 		if self.polygons[selectedFaceNeighbors[0]].selected != True:
		# 			nextFace = selectedFaceNeighbors[0]

		# self.polygons[nextFace].selected = True
		return nextVertex

	def selectPolygons(self, selectedVertices):

		selectdPolygons = []

		for index in selectedVertices:

			connectedPolygons = self.vertex[index].connectedFaces

			for polygon in connectedPolygons:
				if os.path.exists("c:/break"): break
				if self.polygons[polygon].position.y > self.vertex[index].position.y and self.polygons[polygon].selected == False and self.polygons[polygon].normal.y < 0.6:
					print "polygon index ",polygon
					print "normal", self.polygons[polygon].normal.y
					self.polygons[polygon].selected = True
					selectdPolygons.append(polygon)

		return selectdPolygons
	
	def dotProduct(self,poit1,point2):

		return poit1.x*point2.x+poit1.y*point2.y+poit1.z*point2.z


#######################################################################################################################


class VertexData:

#----------------------------------------------------------------------------------------------------------------------
	def __init__(self):
		self.selected = False
		self.connectedEdges = []
		self.connectedFaces = []
		self.connectedVertices= []
		self.position = om.MPoint(0,0,0)
		self.numberOfNeighbors = 0

class EdgeData:

#----------------------------------------------------------------------------------------------------------------------
	def __init__(self):
		self.selected = False
		self.normalAngel = 0.0
		self.connectedEdges = []
		self.edgePosition = om.MPoint(0,0,0)
		self.numberOfNeighbors = 0



class PolyData:

#----------------------------------------------------------------------------------------------------------------------
	def __init__(self):
		self.selected = False
		self.normalAngel = 0.0
		self.connectedFaces = []
		self.vertices = []
		self.position = om.MPoint(0,0,0)
		self.normal = om.MVector(0,0,0)
		self.faceMatrix = om.MMatrix()

#----------------------------------------------------------------------------------------------------------------------
	def __str__(self):
		endStr = '\n'
		outStr = ''
		outStr += ', selected = ' + str(self.selected) + endStr
		for key in self.connectedFaces:
			outStr += '[' + str(key) + '] = ' + str(self.connectedFaces[key]) + endStr
		return outStr

#######################################################################################################################


def run():
	classObj = polySelector()
	return classObj



	