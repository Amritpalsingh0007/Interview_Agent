import { useState, useCallback, useRef } from "react";
import { LiveKitRoom, RoomAudioRenderer, useRoomContext } from "@livekit/components-react";
import "@livekit/components-styles";
import SimpleVoiceAssistant from "./SimpleVoiceAssistant";
import {
  useVoiceAssistant,
  BarVisualizer,
  VoiceAssistantControlBar,
  useTrackTranscription,
  useLocalParticipant,
} from "@livekit/components-react";
import { Track, RoomEvent } from "livekit-client";
import { useEffect } from "react";
import "./SimpleVoiceAssistant.css";

const Message = ({ type, text }) => {
  return (
    <div className="message">
      <strong className={`message-${type}`}>
        {type === "agent" ? "Agent: " : "You: "}
      </strong>
      <span className="message-text">{text}</span>
    </div>
  );
};

const VoiceAssistantInterface = () => {
  const [userSpeech, setUserSpeech] = useState("");
  const [question, setQuestion] = useState("");
  const [llmResponse, setLLMResponse] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const { state, audioTrack, agentTranscriptions } = useVoiceAssistant();
  const localParticipant = useLocalParticipant();
  const [agentIdentity, setAgentIdentity] = useState(null);
  const { segments: userTranscriptions } = useTrackTranscription({
    publication: localParticipant.microphoneTrack,
    source: Track.Source.Microphone,
    participant: localParticipant.localParticipant,
  });
  const called = useRef(false);
  const room = useRoomContext();
  const [messages, setMessages] = useState([]);
  const questionLoader = async()=>{
    if(room.state != "connected") return
    if (called.current) return; // skip if already called
    called.current = true;
    try {
      const response = await room.localParticipant.performRpc({
        destinationIdentity: agentIdentity,
        method: 'confirm_answer',
        payload: 'first_request',
        responseTimeout: 15000
      });
      setQuestion(response)
      console.log('✅ RPC 1 response: ', response);
    } catch (error) {
      console.error('❌ RPC call failed:', error);
    }
  }
  useEffect(() => {
    const handleData = (payload, participant, kind) => {
      const message = new TextDecoder().decode(payload);
      if (message === "agent-ready") {
        console.log("✅ Agent is ready, sending RPC...");
        setAgentIdentity(participant.identity);
      }
    };

    room.on(RoomEvent.DataReceived, handleData);
    return () => {
      room.off(RoomEvent.DataReceived, handleData);
    };
  }, [room]);

  useEffect(() => {
    if (agentIdentity && !called.current && room.state === "connected") {
      questionLoader();
    }
  }, [agentIdentity, room.state]);

  useEffect(() => {
  const allMessages = [
    ...(agentTranscriptions?.map((t) => ({ ...t, type: "agent" })) ?? []),
    ...(userTranscriptions?.map((t) => ({ ...t, type: "user" })) ?? []),
  ].sort((a, b) => a.firstReceivedTime - b.firstReceivedTime);

  setMessages(allMessages);

  const lastMessage = allMessages.at(-1);

  if (!lastMessage) return; // Avoid all following logic if there's no message

  if (lastMessage.type === "agent") {
      setLLMResponse(lastMessage.text);
  }

  if (lastMessage.type === "user") {
      setUserSpeech(lastMessage.text);
  }
}, [agentTranscriptions, userTranscriptions]);



  const handleSkipQuestion = () => {
    setUserSpeech("");
    callAgent('skip_question');
    setLLMResponse(prev=>"");
    console.log("Question skipped");
  };

  const handleReAnswer = () => {
    setIsProcessing(true);
    // Simulate re-processing
    callAgent('re_answer');
    setLLMResponse(prev=>"");
    setIsProcessing(false);
  };
  const callAgent = async(methodName, payload="")=>{
    try {
      const response = await room.localParticipant.performRpc({
        destinationIdentity: agentIdentity,
        method: methodName,
        payload: payload,
        responseTimeout: 30000
      });
      if(methodName === "re_answer" ){
        setIsProcessing(false)
      } else{
        setQuestion(response)
      }
      console.log('✅ RPC response:', response);
    } catch (error) {
      console.error('❌ RPC call failed:', error);
    }
  }
  const handleConfirmAnswer = () => {
    console.log(`SENDING CONFIRM ANSWER llmResponse ${llmResponse}`)
    callAgent("confirm_answer", llmResponse);
    setLLMResponse(prev => "");
  };

  return (
    <div className="voice-assistant-container">
      <div className="main-interface">
        <div className="left">
          {/* Header */}
          <div className="speech-section">
            <div className="section-header">
              <span className="arrow">↘</span>
              <span className="section-title">Question</span>
            </div>
            <div className="speech-content">
              <div className="content-box">
                <div className="content-label">
                  Div for showing question from LLM output
                </div>
                {question && <div className="speech-text">{question}</div>}
                {!question && (
                  <div className="placeholder-text">
                    What is this ? a demo question?
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Speech Input Section */}
          <div className="speech-section">
            <div className="section-header">
              <span className="arrow">↘</span>
              <span className="section-title">what you have spoken.</span>
            </div>
            <div className="speech-content">
              <div className="content-box">
                <div className="content-label">
                  Div for showing text from STT output of what user have spoken
                </div>
                {userSpeech && <div className="speech-text">{userSpeech}</div>}
                {!userSpeech && (
                  <div className="placeholder-text">
                    Listening for your speech...
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* LLM Response Section */}
          <div className="response-section">
            <div className="section-header">
              <span className="arrow">↘</span>
              <span className="section-title">What I have understood.</span>
            </div>
            <div className="response-content">
              <div className="content-box">
                <div className="content-label">
                  Div for showing output from LLM
                </div>
                {isProcessing && (
                  <div className="processing-text">
                    Processing your request...
                  </div>
                )}
                {llmResponse && !isProcessing && (
                  <div className="response-text">{llmResponse}</div>
                )}
                {!llmResponse && !isProcessing && (
                  <div className="placeholder-text">
                    Waiting for response...
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button
              className="action-btn skip-btn"
              onClick={handleSkipQuestion}
            >
              Skip question
            </button>
            <button
              className="action-btn reanswer-btn"
              onClick={handleReAnswer}
              disabled={!userSpeech}
            >
              Re answer
            </button>
            <button
              className="action-btn confirm-btn"
              onClick={handleConfirmAnswer}
              disabled={!llmResponse || isProcessing}
            >
              Confirm Answer
            </button>
          </div>

        </div>
        <hr style={{ margin: "10px" }} />
        <div className="right">
          <div className="voice-assistant-container">
            <div className="visualizer-container">
              <BarVisualizer state={state} barCount={5} trackRef={audioTrack} />
            </div>
            <div className="control-section">
              <VoiceAssistantControlBar />
              <div className="conversation">
                {messages.map((msg, index) => (
                  <Message
                    key={msg.id || index}
                    type={msg.type}
                    text={msg.text}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .voice-assistant-container {
          margin: 0 auto;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
        }

        .main-interface {
          border: 3px solid #ccc;
          border-radius: 8px;
          padding: 20px;
          background: #fafafa;
          display: flex;
        }

        .header-section {
          margin-bottom: 20px;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px;
          border: 2px solid #999;
          border-radius: 4px;
          background: white;
          font-size: 14px;
        }

        .status-dot {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: #ccc;
        }

        .status-dot.listening {
          background: #4caf50;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
          100% {
            opacity: 1;
          }
        }

        .speech-section,
        .response-section {
          margin: 20px 0;
        }

        .section-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 10px;
          font-size: 16px;
          font-weight: 500;
        }

        .arrow {
          font-size: 20px;
          color: #666;
        }

        .speech-content,
        .response-content {
          margin-left: 28px;
        }

        .content-box {
          border: 2px solid #999;
          border-radius: 4px;
          background: white;
          min-height: 80px;
        }

        .content-label {
          padding: 8px 12px;
          background: #f0f0f0;
          border-bottom: 1px solid #ddd;
          font-size: 12px;
          color: #666;
        }

        .speech-text,
        .response-text {
          padding: 15px;
          font-size: 14px;
          line-height: 1.5;
          color: #333;
        }

        .placeholder-text {
          padding: 15px;
          font-size: 14px;
          color: #999;
          font-style: italic;
        }

        .processing-text {
          padding: 15px;
          font-size: 14px;
          color: #2196f3;
          font-style: italic;
        }

        .action-buttons {
          display: flex;
          gap: 15px;
          justify-content: center;
          margin-top: 30px;
          flex-wrap: wrap;
        }

        .action-btn {
          padding: 10px 20px;
          border: 2px solid #999;
          border-radius: 4px;
          background: white;
          font-size: 14px;
          cursor: pointer;
          transition: all 0.2s;
          min-width: 120px;
        }

        .action-btn:hover:not(:disabled) {
          background: #f0f0f0;
          transform: translateY(-1px);
        }

        .action-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .skip-btn:hover:not(:disabled) {
          border-color: #ff9800;
          background: #fff3e0;
        }

        .reanswer-btn:hover:not(:disabled) {
          border-color: #2196f3;
          background: #e3f2fd;
        }

        .confirm-btn:hover:not(:disabled) {
          border-color: #4caf50;
          background: #e8f5e8;
        }

        .demo-controls {
          margin-top: 40px;
          padding: 20px;
          background: #f5f5f5;
          border-radius: 8px;
          border: 2px dashed #ccc;
        }

        .demo-controls h3 {
          margin: 0 0 15px 0;
          color: #666;
          font-size: 16px;
        }

        .demo-buttons {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }

        .demo-btn {
          padding: 8px 16px;
          border: 1px solid #ddd;
          border-radius: 4px;
          background: white;
          font-size: 12px;
          cursor: pointer;
          transition: background 0.2s;
        }

        .demo-btn:hover {
          background: #e9e9e9;
        }

        .clear-btn {
          background: #ffebee;
          border-color: #f44336;
          color: #f44336;
        }

        .clear-btn:hover {
          background: #ffcdd2;
        }

        @media (max-width: 600px) {
          .voice-assistant-container {
            padding: 10px;
          }

          .action-buttons {
            flex-direction: column;
            align-items: center;
          }

          .demo-buttons {
            flex-direction: column;
          }
        }
      `}</style>
    </div>
  );
};

const LiveKitModal = ({ setShowSupport }) => {
  const [isSubmittingName, setIsSubmittingName] = useState(true);
  const [name, setName] = useState("");
  const [token, setToken] = useState(null);

  const getToken = useCallback(async (userName) => {
    try {
      console.log("run");
      const response = await fetch(
        `/api/getToken?name=${encodeURIComponent(userName)}`
      );
      const token = await response.text();
      console.log("Token : " + token);
      setToken(token);
      setIsSubmittingName(false);
    } catch (error) {
      console.error(error);
    }
  }, []);

  const handleNameSubmit = (e) => {
    if (e) e.preventDefault();
    if (name.trim()) {
      getToken(name);
    }
  };

  return (
    <div
      className="modal-overlay"
      style={{
        //   position: 'fixed',
        //   top: 0,
        //   left: 0,
        //   right: 0,
        //   bottom: 0,
        //   background: 'rgba(0,0,0,0.5)',
        //   zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
      }}
    >
      <div
        className="modal-content"
        style={{
          background: "white",
          borderRadius: "8px",
          padding: "20px",
          //   maxWidth: "90vw",
          //   maxHeight: "90vh",
          overflow: "auto",
          width: "100%",
        }}
      >
        <div className="support-room">
          {isSubmittingName ? (
            <div
              className="name-form"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "15px",
                alignItems: "center",
              }}
            >
              <h2>Enter your name to connect with support</h2>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                onKeyPress={(e) => {
                  if (e.key === "Enter" && name.trim()) {
                    handleNameSubmit(e);
                  }
                }}
                style={{
                  padding: "10px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  //   width: "250px",
                }}
              />
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  onClick={handleNameSubmit}
                  disabled={!name.trim()}
                  style={{
                    padding: "10px 20px",
                    background: name.trim() ? "#2196F3" : "#ccc",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: name.trim() ? "pointer" : "not-allowed",
                  }}
                >
                  Connect
                </button>
                <button
                  onClick={() => setShowSupport(false)}
                  style={{
                    padding: "10px 20px",
                    background: "#f44336",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : token ? (
            <LiveKitRoom
              serverUrl={import.meta.env.VITE_LIVEKIT_URL}
              token={token}
              connect={true}
              video={false}
              audio={true}
              onDisconnected={() => {
                setShowSupport(false);
                setIsSubmittingName(true);
              }}
            >
              <RoomAudioRenderer />
              <VoiceAssistantInterface />
            </LiveKitRoom>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default LiveKitModal;
