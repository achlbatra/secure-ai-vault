import '../styles/Auth.css';
import logo from '../assets/logo.png';
import React, {useState} from 'react';
import { useNavigate } from 'react-router-dom';
import LoginPage from './LoginPage';

const RegisterPage = () => {

  const [email, setEmail] = useState('');
  const [role, setRole] = useState('user');
  const [department, setDepartment] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    const formDetails = {
      email: email,
      role: role,
      department: department,
      password: password
    };

    try {
      const response = await fetch('http://localhost:8000/auth/register', {
        method: 'POST', 
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formDetails)
      });
      const data = await response.json();
      if (response.ok) {
        console.log('Registration successful:', data);
        navigate('/login');
      } else {
        setError(data.detail || 'Registration failed. Please try again.');
        setLoading(false);
      } 
      } catch (error) {
        console.error('Error during registration:', error);
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
          <h3>Sign Up</h3>
          <p>Get started for free!</p>
        </div>
        <div className='login-form'>
          <form onSubmit={handleSubmit}>
            <div className='form-group'>  
              <label htmlFor='email'>Email</label>
              <input type='email' id='email' name='email' required onChange={(e)=>setEmail(e.target.value)}/>
            </div>
            <div className='form-group'>
              <label htmlFor='role'>Role</label>
              <select id='role' name='role' required onChange={(e)=>setRole(e.target.value)}>
                <option value='user'>User</option>
                <option value='admin'>Admin</option>
                <option value='compliance'>Compliance</option>
              </select>
            </div>
            <div className='form-group'>
              <label htmlFor='department'>Department</label>
              <input type='text' id='department' name='department' required onChange={(e)=>setDepartment(e.target.value)}/>
            </div>
            <div className='form-group'>
              <label htmlFor='password'>Password</label>
              <input type='password' id='password' name='password' required onChange={(e)=>setPassword(e.target.value)}/>
            </div>
            <button type='submit' className='register-button' disabled={loading}>{loading ? 'Creating your account...' : 'Sign up'}</button>
          </form>
          {error && <p className='error-message'>{error}</p>}
        </div>
      </div>  
      <div className='form-footer'>
      <p>
        Already have an account?{" "}
        <button 
          onClick={() => navigate("/login")} 
          className="link-button"
        >
          Login
        </button>
      </p>
      </div>
    </>
  )
}

export default RegisterPage;