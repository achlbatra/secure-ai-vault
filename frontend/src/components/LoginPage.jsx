import '../styles/Auth.css'
import logo from '../assets/logo.png';
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';


const LoginPage = () => {

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate(); 

  const validateForm = () => {
    if (!email || !password) {
      setError('Please fill in all fields.');
      return false;
    }
    setError('');
    return true;
  };

  const handleSubmit = async (e) => {
  e.preventDefault();
  if (!validateForm()) return;  
  setLoading(true);

  const formData = new URLSearchParams();
  formData.append("username", email);  // OAuth2 expects 'username'
  formData.append("password", password);  // OAuth2 expects 'password'

  try {
    const response = await fetch('http://localhost:8000/auth/login', {
      method: 'POST', 
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: formData
    });

    const data = await response.json();

    if (response.ok) {
      localStorage.setItem('token', data.access_token);
      navigate('/dashboard');
    } else {
      setError(data.detail || 'Login failed. Please try again.');
    }
  } catch (error) {
    console.error('Error during login:', error);
    setError('An error occurred. Please try again.');
  }
  setLoading(false);
};

  return (
    <>
      <div className='logo-img'>
        <img src={logo} alt="Secure AI Vault Logo" />
      </div>
      <div className='container'>
        <div className='login-header'>
          <h3>Login</h3>
        </div>
        <div className='login-form'>
          <form onSubmit={handleSubmit}>
            <div className='form-group'>  
              <label htmlFor='email' >Email</label>
              <input type='email' id='email' name='email' required onChange={(e)=>setEmail(e.target.value)}/>
            </div>
            <div className='form-group'>
              <label htmlFor='password'>Password</label>
              <input type='password' id='password' name='password' required onChange={(e)=>setPassword(e.target.value)}/>
            </div>
            <button type='submit' className='login-button' disabled={loading}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
            {error && <p className='error-message'>{error}</p>}
          </form>
        </div>
      </div>  
      <div className='form-footer'>
      <p>
        Don't have an account?{" "}
        <button 
          onClick={() => navigate("/")} 
          className="link-button"
        >
        Create now
        </button>
      </p>
      </div>
    </>
  )
}
export default LoginPage;