import { useState } from 'react'
import './App.css'
// import LiveKitModal from './components/LiveKitModal';
import LiveKitModal from './components/VoiceAssistantInterface';

function App() {
  const [showSupport, setShowSupport] = useState(false);

  const handleSupportClick = () => {
    setShowSupport(true)
  }

  return (
    <>
      {/* <LiveKitModal setShowSupport={setShowSupport}/> */}
      <LiveKitModal/>
      </>
  )
}

export default App
