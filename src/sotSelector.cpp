/*+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 * Copyright Projet JRL-Japan, 2007
 *+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 *
 * File:      sotSelector.h
 * Project:   SOT
 * Author:    Nicolas Mansard
 *
 * Version control
 * ===============
 *
 *  $Id$
 *
 * Description
 * ============
 *
 *
 * ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++*/

#include <sot/sotSelector.h>
#include <sot-core/debug.h>
#include <dynamic-graph/factory.h>
#include <sot-pattern-generator/exception-pg.h>

DYNAMICGRAPH_FACTORY_ENTITY_PLUGIN(sotSelector,"Selector");



sotSelector::
sotSelector( const std::string & name ) 
  :Entity(name)
  ,selectorSIN( NULL,"sotSelector("+name+")::input(uint)::selec" )
{
  sotDEBUGIN(5);
  
  signalRegistration( selectorSIN );

  sotDEBUGOUT(5);
}


sotSelector::
~sotSelector( void )
{
  sotDEBUGIN(5);

  resetSignals(0,0);

  sotDEBUGOUT(5);
  return;
}

/* --- SIGNALS -------------------------------------------------------------- */
/* --- SIGNALS -------------------------------------------------------------- */
/* --- SIGNALS -------------------------------------------------------------- */
#define SOT_CALL_SIG(sotName,sotType)          \
  boost::bind(&Signal<sotType,int>::access, \
	      &sotName,_2)

template< class T >
unsigned int sotSelector::
createSignal( const std::string& shortname,const int & sigId__)
{
  sotDEBUGIN(15);
  
  unsigned int sigId = sigId__;
  /*  If sigId is not valid, it is set to the first free signal. */
  if ( (sigId<0)||(sigId>nbSignals) )
    for( unsigned int i=0;i<nbSignals;++i )
      if( 0==inputsSIN[i].size() ){ sigId=i; break; }
  if ( (sigId<0)||(sigId>nbSignals) ) return -1;
  
  /* Set up the input signal vector. */
  std::vector< sotSignalAbstract<int>* >& entriesSIN = inputsSIN[sigId];
  for( unsigned int i=0;i<entriesSIN.size();++i )
    {
      if( NULL!=entriesSIN[i] ) 
	{
	  signalDeregistration( entriesSIN[i]->getName() );
	  delete entriesSIN[i]; 
	}
    }
  entriesSIN.resize( nbEntries );
  
  /* sigDep contains the list of the input signal. sigOut depends of these. */
  SignalArray<int> sigDep;
  std::ostringstream signame;

  /* Set the entries. */
  for( unsigned int i=0;i<nbEntries;++i )
    {
      signame.str("");
      signame << "sotSelector(" << Entity::getName() <<")::input("
	      << typeid(T).name() << ")::" << shortname << i;
      SignalPtr<T,int> * sigIn = new SignalPtr<T,int>( NULL,signame.str() );
      inputsSIN[sigId][i] = sigIn; 

      signalRegistration( *sigIn );
      sigDep << (*sigIn);
    }

  /* Set the output. */
  if( NULL!=outputsSOUT[sigId] ) 
    {
      signalDeregistration( outputsSOUT[sigId]->getName() );
      delete outputsSOUT[sigId]; 
    }
  signame.str("");
  signame << "sotSelector(" << Entity::getName() <<")::output("
	  << typeid(T).name() << ")::" << shortname;
  
  SignalTimeDependent<T,int> * sigOut 
    = new SignalTimeDependent<T,int>
    ( boost::bind(&sotSelector::computeSelection<T>,
		  SOT_CALL_SIG(selectorSIN,unsigned int),
		  boost::ref(entriesSIN),_1,_2), 
      sigDep<<selectorSIN,
      signame.str() );
  outputsSOUT[sigId] = sigOut;
  signalRegistration( *sigOut );
  sigOut->setReady(true);
  
  sotDEBUGOUT(15);
  return sigId;
}

template< class T >
T& sotSelector::
computeSelection( const unsigned int & sigNum,
		  std::vector< sotSignalAbstract<int>* >& entriesSIN,
		  T& res,const int& time )
{
  sotDEBUGIN(15);
  
  sotDEBUG(25) << "Type " << typeid(T).name() << std::endl;

  if( (sigNum<0)||(sigNum>entriesSIN.size()) ) 
    {
      SOT_THROW ExceptionPatternGenerator( ExceptionPatternGenerator::SELECTOR_RANK,
					      "Rank of the selector is not valid. ",
					      "(while calling outputsSOUT with selector"
					      "=%d).",sigNum );
    }
      
  
  sotDEBUG(25) << "Sig name " << entriesSIN[sigNum]->getName() << std::endl;
  SignalPtr<T,int> * sigSpec 
    = dynamic_cast< SignalPtr<T,int>* >( entriesSIN[sigNum]);
  if( NULL==sigSpec )
    {
      SOT_THROW ExceptionPatternGenerator( ExceptionPatternGenerator::BAD_CAST,
					      "Signal types for IN and OUT uncompatible. ",
					      "(while calling outputsSOUT of sig<%d>"
					      "with output type %s and input of %s).",
					      sigNum,(typeid(T).name()),
					      (typeid(*entriesSIN[sigNum]).name()) );
    }

  res = sigSpec->access(time);
  sotDEBUGOUT(15);
  return res;
}

void sotSelector::
resetSignals( const unsigned int & nbEntries__,
	      const unsigned int & nbSignals__ )
{
  for( std::vector< std::vector< sotSignalAbstract<int>* > >::iterator 
	 iter=inputsSIN.begin();iter<inputsSIN.end();++iter )
    {
      for( std::vector< sotSignalAbstract<int>* >::iterator 
	     iterSig=iter->begin();iterSig<iter->end();++iterSig )
	{
	  sotSignalAbstract<int>* sigPtr = *iterSig;
	  if( NULL!=sigPtr ) delete sigPtr;
	}
    }
  inputsSIN.resize( nbSignals__ );
  nbSignals = nbSignals__;
  nbEntries = nbEntries__;

  for( std::vector< sotSignalAbstract<int>* >::iterator 
	 iterSig=outputsSOUT.begin();iterSig<outputsSOUT.end();++iterSig )
    {
      sotSignalAbstract<int>* sigPtr = *iterSig;
      if( NULL!=sigPtr ) delete sigPtr;
    }
  outputsSOUT.resize( nbSignals );
}


/* --- PARAMS --------------------------------------------------------------- */
/* --- PARAMS --------------------------------------------------------------- */
/* --- PARAMS --------------------------------------------------------------- */

#define SOT_SELECTOR_CREATE_TYPE( sotType,sotTypeName )                        \
      if( dORc&&(type==sotTypeName) )                                          \
	selec.createSignal<sotType>( name,sigId );                             \
      else oss << "  - " << sotTypeName << std::endl;

static void
displayOrCreate( sotSelector& selec,
		 bool dORc,std::ostream& os,
		 const std::string& name="",const std::string& type="",
		 const int & sigId=-1 )
{
  std::ostringstream oss;

  /* ------------------------------------------------------------------------ */
  /* *** Enter here the type list *** --------------------------------------- */
  /* ------------------------------------------------------------------------ */

  SOT_SELECTOR_CREATE_TYPE( ml::Vector,"vector" );
  SOT_SELECTOR_CREATE_TYPE( ml::Matrix,"matrix" );
  SOT_SELECTOR_CREATE_TYPE( MatrixHomogeneous,"matrixHomo" );

  /* ------------------------------------------------------------------------ */
  /* ------------------------------------------------------------------------ */

  if(! dORc ) os << "Types available:" << std::endl << oss.str();
}



void sotSelector::
commandLine( const std::string& cmdLine,
	     std::istringstream& cmdArgs,
	     std::ostream& os )
{
  if( cmdLine == "help" )
    {
      os << "Selector: " << std::endl
	 << "  - typeList: display the available types. " << std::endl
	 << "  - reset <nbEntries> <nbSig>: reset the signal lists. " << std::endl
	 << "  - create <sigtype> <signame> <sigid>: create a new set of signals" << std::endl;
    }
  else if( cmdLine == "typeList" ) { displayOrCreate( *this,false,os ); }
  else if( cmdLine == "create" )
    {
      std::string type,name; int sigId;
      cmdArgs >> type >> name >>std::ws;
      if( cmdArgs.good() ) cmdArgs >> sigId; else sigId=-1;
      displayOrCreate( *this,true,os,name,type,sigId ); 

    }
  else if( cmdLine == "reset" )
    {
      cmdArgs >> std::ws;
      if( cmdArgs.good() )
	{
	  unsigned int nbSig,nbEntries; cmdArgs>>nbSig>> std::ws; 
	  if( cmdArgs.good() ) cmdArgs>>nbEntries; 
	  else 
	    {os << "Error: usage is: reset <nbEntries> <nbSig>." << std::endl; return;}
	  resetSignals(nbSig,nbEntries);
	}
      else {os << "Error: usage is: reset <nbEntries> <nbSig>." << std::endl; return;}
    }
  else { Entity::commandLine( cmdLine,cmdArgs,os); }
}

